from typing import override

from middleware.adapters.azure.azure_foundry_adapter import AzureMsFoundryAppAdapter
from middleware.adapters.azure.ms_foundry.constants import AGENT_NAME_HR_ASSISTANT
from middleware.adapters.azure.ms_foundry.hr_assistant_agent.memory_store import HrMemoryStore
from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory
from middleware.adapters.daos.objects_factory import ObjectsFactory as DaoObjectsFactory
from middleware.common.app_exec_contants import AppExecConstants
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
        objects_factory = ObjectsFactory.get_instance()
        conversation_id = self.get_or_create_conversation_id(ctx.req.session_id, objects_factory)
        get_logger(__name__).info(
            "session_id=%s conversation_id=%s joiner_info_id=%s",
            ctx.req.session_id,
            conversation_id,
            ctx.req.joiner_info_id,
        )
        project_client = objects_factory.get_ms_foundry_project_client()
        self.memory.remember(project_client, ctx.req.joiner_info_id, self._preference_memory(ctx.req.joiner_info_id))
        memories = self.memory.search(project_client, ctx.req.joiner_info_id, ctx.req.query)
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
        ctx.resp.results["output_text"] = answer
        ctx.resp.results["response_id"] = response.id
        ctx.resp.results["model"] = response.model
        ctx.resp.results["status"] = str(response.status)
        ctx.resp.ctx_data["conversation_id"] = conversation_id
        ctx.resp.usage.input_tokens = input_tokens
        ctx.resp.usage.output_tokens = output_tokens
        ctx.resp.usage.total_tokens = total_tokens
        ctx.resp.usage.cached_tokens = cached_tokens
        ctx.resp.usage.reasoning_tokens = reasoning_tokens
        self.memory.remember(
            project_client,
            ctx.req.joiner_info_id,
            f"Question: {ctx.req.query}\nAnswer: {answer}",
        )
        return AppExecConstants.SUCCESS

    def _input(self, joiner_info_id: str, query: str, memories: list[str]) -> str:
        record = self._record(joiner_info_id)
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

    def _record(self, joiner_info_id: str) -> str:
        if not joiner_info_id.strip():
            return ""
        dao = DaoObjectsFactory.get_instance()
        joiner = dao.get_joiner_info_mgr().get(joiner_info_id)
        if joiner is None:
            return ""
        return _joiner_text(joiner)


def _joiner_text(joiner: JoinerInfo) -> str:
    name = " ".join(part for part in (joiner.first_name, joiner.middle_name, joiner.last_name) if part)
    lines = [
        "Joiner record:",
        f"Joiner info id: {joiner.id}",
        f"Name: {name}",
        f"Email: {joiner.email}",
        f"Phone: {joiner.contact_phone}",
        f"Address: {joiner.contact_address}",
        f"Interviewed by ids: {', '.join(joiner.interviewed_by_employee_ids)}",
        f"Interviewed by names: {', '.join(joiner.interviewed_by_employee_names)}",
        f"Official role: {joiner.official_role_name}",
        f"Internal role: {joiner.internal_role_name}",
        f"Joining official role: {joiner.joining_official_role_name}",
        f"Salary accepted USD: {joiner.salary_accepted_usd}",
        f"Joining date: {joiner.joining_date}",
    ]
    return "\n".join(lines)
