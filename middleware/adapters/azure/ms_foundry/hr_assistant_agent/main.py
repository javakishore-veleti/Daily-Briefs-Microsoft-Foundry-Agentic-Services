from time import perf_counter
from typing import override

from middleware.adapters.azure.azure_foundry_adapter import AzureMsFoundryAppAdapter
from middleware.adapters.azure.ms_foundry.constants import AGENT_NAME_HR_ASSISTANT
from middleware.adapters.azure.ms_foundry.hr_assistant_agent.memory_store import HrMemoryStore
from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory
from middleware.adapters.daos.objects_factory import ObjectsFactory as DaoObjectsFactory
from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.app_config import AppConfig
from middleware.common.dtos.common import AppCtx
from middleware.common.dtos.hr_assistant_dtos import HrAssistantReq, HrAssistantResp
from middleware.common.entity.joiner import JoinerInfo
from middleware.common.utils.logger_util import get_logger, log_methods


@log_methods
class HrAssistantAdapter(AzureMsFoundryAppAdapter[HrAssistantReq, HrAssistantResp]):
    def __init__(self) -> None:
        self.name = "HrAssistantAdapter"
        self.description = "An adapter that asks the HR assistant agent about a new joiner"
        self.memory = HrMemoryStore()

    @override
    def run(self, ctx: AppCtx[HrAssistantReq, HrAssistantResp]) -> int:
        started = perf_counter()
        objects_factory = ObjectsFactory.get_instance()
        conversation_id = self.get_or_create_conversation_id(ctx.req.session_id, objects_factory)
        get_logger(__name__).info(
            "session_id=%s conversation_id=%s joiner_info_id=%s",
            ctx.req.session_id,
            conversation_id,
            ctx.req.joiner_info_id,
        )
        project_client = objects_factory.get_ms_foundry_project_client()
        preference_text = self._preference_memory(ctx.req.joiner_info_id)

        search_ms = 0
        update_ms = 0
        mark = perf_counter()
        memories = self.memory.search(project_client, ctx.req.joiner_info_id, ctx.req.query)
        search_ms += _elapsed_ms(mark)
        # Production write policy: seed preferences only on a cold miss.
        # Do not re-write the same Mongo profile on every turn (avoids repeated
        # Foundry extraction cost when memory already has hits for this scope).
        if not memories and preference_text:
            mark = perf_counter()
            self.memory.remember(project_client, ctx.req.joiner_info_id, preference_text, wait=True)
            update_ms += _elapsed_ms(mark)
            mark = perf_counter()
            memories = self.memory.search(project_client, ctx.req.joiner_info_id, ctx.req.query)
            search_ms += _elapsed_ms(mark)

        mark = perf_counter()
        response = objects_factory.get_open_ai_client().responses.create(
            conversation=conversation_id,
            extra_body={
                "agent_reference": {
                    "name": AGENT_NAME_HR_ASSISTANT,
                    "type": "agent_reference",
                }
            },
            input=self._input(ctx.req.joiner_info_id, ctx.req.query, memories),
        )
        agent_ms = _elapsed_ms(mark)
        usage = response.usage
        input_tokens = usage.input_tokens if usage is not None else 0
        output_tokens = usage.output_tokens if usage is not None else 0
        total_tokens = usage.total_tokens if usage is not None else 0
        cached_tokens = (
            usage.input_tokens_details.cached_tokens
            if usage is not None and usage.input_tokens_details is not None
            else 0
        )
        reasoning_tokens = (
            usage.output_tokens_details.reasoning_tokens
            if usage is not None and usage.output_tokens_details is not None
            else 0
        )
        answer = response.output_text
        # Optional async turn memory (off by default). Profile facts come from
        # cold-miss seed or the explicit Memory populate action.
        if (
            AppConfig.get_instance().get_hr_memory_store_turns()
            and _should_store_turn(ctx.req.query, answer)
        ):
            self.memory.remember(
                project_client,
                ctx.req.joiner_info_id,
                f"Question: {ctx.req.query}\nAnswer: {_compact_turn_answer(answer)}",
                wait=False,
            )
        total_ms = _elapsed_ms(started)
        slowest_step, slowest_ms = _slowest(
            ("Memory search", search_ms),
            ("Memory update", update_ms),
            ("HR agent reply", agent_ms),
        )
        ctx.resp.results["output_text"] = answer
        ctx.resp.results["response_id"] = response.id
        ctx.resp.results["model"] = response.model
        ctx.resp.results["status"] = str(response.status)
        ctx.resp.results["total_ms"] = str(total_ms)
        ctx.resp.results["memory_search_ms"] = str(search_ms)
        ctx.resp.results["memory_update_ms"] = str(update_ms)
        ctx.resp.results["agent_ms"] = str(agent_ms)
        ctx.resp.results["slowest_step"] = slowest_step
        ctx.resp.results["slowest_ms"] = str(slowest_ms)
        ctx.resp.ctx_data["conversation_id"] = conversation_id
        ctx.resp.usage.input_tokens = input_tokens
        ctx.resp.usage.output_tokens = output_tokens
        ctx.resp.usage.total_tokens = total_tokens
        ctx.resp.usage.cached_tokens = cached_tokens
        ctx.resp.usage.reasoning_tokens = reasoning_tokens
        get_logger(__name__).info(
            "timing total_ms=%s search_ms=%s update_ms=%s agent_ms=%s slowest=%s",
            total_ms,
            search_ms,
            update_ms,
            agent_ms,
            slowest_step,
        )
        return AppExecConstants.SUCCESS

    def _input(self, joiner_info_id: str, query: str, memories: list[str]) -> str:
        # When memory already has profile hits, send a slim identity header to cut tokens.
        # On cold miss (no memories), send the fuller joiner record for grounding.
        record = self._record(joiner_info_id, compact=bool(memories))
        parts = [record, f"Question: {query}"]
        if memories:
            parts.insert(1, "Memory context:\n" + "\n".join(memories))
        return "\n\n".join(part for part in parts if part)

    def _preference_memory(self, joiner_info_id: str) -> str:
        if not joiner_info_id.strip():
            return ""
        dao = DaoObjectsFactory.get_instance()
        joiner = dao.get_joiner_info_mgr().get(joiner_info_id)
        if joiner is None:
            return ""
        preferences = dao.get_joiner_preferences_mgr().for_joiner(joiner_info_id)
        if preferences is None:
            return ""
        name = " ".join(part for part in (joiner.first_name, joiner.middle_name, joiner.last_name) if part)
        return (
            f"Remember this profile for {name}. "
            f"Food preferences: {preferences.food_preferences}. "
            f"Personal interests: {preferences.personal_interests}. "
            f"Resumes: {preferences.resumes}."
        )

    def _record(self, joiner_info_id: str, compact: bool = False) -> str:
        if not joiner_info_id.strip():
            return ""
        dao = DaoObjectsFactory.get_instance()
        joiner = dao.get_joiner_info_mgr().get(joiner_info_id)
        if joiner is None:
            return ""
        return _joiner_text(joiner, compact=compact)


def _joiner_text(joiner: JoinerInfo, compact: bool = False) -> str:
    name = " ".join(part for part in (joiner.first_name, joiner.middle_name, joiner.last_name) if part)
    lines = [
        "Joiner record:",
        f"Joiner info id: {joiner.id}",
        f"Name: {name}",
        f"Email: {joiner.email}",
        f"Official role: {joiner.official_role_name}",
        f"Joining official role: {joiner.joining_official_role_name}",
        f"Joining date: {joiner.joining_date}",
    ]
    if not compact:
        lines[4:4] = [
            f"Phone: {joiner.contact_phone}",
            f"Address: {joiner.contact_address}",
            f"Interviewed by ids: {', '.join(joiner.interviewed_by_employee_ids)}",
            f"Interviewed by names: {', '.join(joiner.interviewed_by_employee_names)}",
            f"Internal role: {joiner.internal_role_name}",
            f"Salary accepted USD: {joiner.salary_accepted_usd}",
        ]
    return "\n".join(lines)


def _should_store_turn(query: str, answer: str) -> bool:
    q = query.strip()
    a = answer.strip()
    if len(q) < 3 or len(a) < 12:
        return False
    lowered = a.lower()
    blocked = (
        "no memory",
        "do not have",
        "don't have",
        "not found",
        "failed",
        "unauthorized",
        "401",
        "403",
    )
    return not any(token in lowered for token in blocked)


def _compact_turn_answer(answer: str, limit: int = 500) -> str:
    text = " ".join(answer.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _elapsed_ms(started: float) -> int:
    return max(0, int((perf_counter() - started) * 1000))


def _slowest(*steps: tuple[str, int]) -> tuple[str, int]:
    name, ms = max(steps, key=lambda item: item[1])
    if ms <= 0:
        return ("", 0)
    return (name, ms)
