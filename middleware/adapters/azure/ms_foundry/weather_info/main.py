import json
import urllib.error
import urllib.request
from typing import override
from urllib.parse import quote

from middleware.adapters.azure.azure_foundry_adapter import AzureMsFoundryAppAdapter
from middleware.adapters.azure.ms_foundry.constants import AGENT_NAME_WEATHER
from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory
from middleware.adapters.azure.ms_foundry.weather_info.weather_report import WeatherReport
from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.app_module import AppModule
from middleware.common.dtos.common import AppCtx
from middleware.common.dtos.weather_info_dtos import WeatherInfoReq, WeatherInfoResp
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.common.utils.session_cache import SessionCache


@log_methods
class WeatherInfoAdapter(AzureMsFoundryAppAdapter[WeatherInfoReq, WeatherInfoResp]):
    def __init__(self):
        self.name = "WeatherInfoAdapter"
        self.description = "An adapter that can get weather information from the open api"

    @override
    def run(self, ctx: AppCtx[WeatherInfoReq, WeatherInfoResp]) -> int:
        objects_factory = ObjectsFactory.get_instance()
        conversation_id = self.get_or_create_conversation_id(ctx.req.session_id, objects_factory)
        get_logger(__name__).info(
            "session_id=%s conversation_id=%s",
            ctx.req.session_id,
            conversation_id,
        )

        client = objects_factory.get_open_ai_client()
        response = client.responses.create(
            conversation=conversation_id,
            extra_body={
                "agent_reference": {
                    "name": AGENT_NAME_WEATHER,
                    "type": "agent_reference",
                }
            },
            input=ctx.req.query,
        )
        answer = self._answer_text(response)
        place = self._remembered_place(ctx.req.session_id, ctx.req.query, response)
        report = WeatherReport().compose(place, ctx.req.query)
        if report:
            answer = report
            self._remember_place(ctx.req.session_id, place)
        elif not answer:
            answer = self._forecast_from_place(place)
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
        get_logger(__name__).info(
            "session_id=%s conversation_id=%s response_id=%s model=%s status=%s input_tokens=%s output_tokens=%s total_tokens=%s cached_tokens=%s reasoning_tokens=%s",
            ctx.req.session_id,
            conversation_id,
            response.id,
            response.model,
            response.status,
            input_tokens,
            output_tokens,
            total_tokens,
            cached_tokens,
            reasoning_tokens,
        )
        return AppExecConstants.SUCCESS

    def _answer_text(self, response: object) -> str:
        messages: list[str] = []
        tool_raw = ""
        for item in getattr(response, "output", None) or []:
            data = item.model_dump() if hasattr(item, "model_dump") else {}
            kind = data.get("type")
            if kind == "openapi_call_output":
                tool_raw = self._tool_output_text(data)
            if kind != "message":
                continue
            for part in data.get("content") or []:
                if not isinstance(part, dict) or part.get("type") != "output_text":
                    continue
                text = str(part.get("text") or "").strip()
                if text and not self._is_tool_trace(text):
                    messages.append(text)
        if messages:
            return messages[-1]
        forecast = self._forecast_from_tool(tool_raw)
        if forecast:
            return forecast
        fallback = str(getattr(response, "output_text", "") or "").strip()
        if fallback and not self._is_tool_trace(fallback):
            return fallback
        return forecast

    def _tool_output_text(self, data: dict) -> str:
        for key in ("output", "result"):
            value = data.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, list):
                parts = [str(part.get("text") or part) for part in value if isinstance(part, (dict, str))]
                return "\n".join(part for part in parts if part)
        return ""

    def _place(self, query: str, response: object | None) -> str:
        for item in getattr(response, "output", None) or []:
            data = item.model_dump() if hasattr(item, "model_dump") else {}
            if data.get("type") != "openapi_call":
                continue
            arguments = data.get("arguments")
            if not isinstance(arguments, str):
                continue
            try:
                payload = json.loads(arguments)
            except json.JSONDecodeError:
                continue
            location = str(payload.get("location") or "").strip()
            if location:
                return location
        lowered = query.lower()
        for marker in (" in ", " at ", " for "):
            index = lowered.rfind(marker)
            if index >= 0:
                place = query[index + len(marker) :].strip(" ?.")
                if place:
                    return place
        return ""

    def _remembered_place(self, session_id: str, query: str, response: object) -> str:
        named = self._place(query, response)
        if named:
            return named
        cached = str(SessionCache.get_instance().get(session_id).get("place") or "").strip()
        if cached:
            return cached
        return self._place_from_history(session_id)

    def _remember_place(self, session_id: str, place: str) -> None:
        cache = SessionCache.get_instance()
        session = cache.get(session_id)
        session["place"] = place
        cache.set(session_id, session)

    def _place_from_history(self, session_id: str) -> str:
        if not session_id.strip():
            return ""
        try:
            from middleware.adapters.daos.objects_factory import ObjectsFactory as DaoObjectsFactory

            messages = DaoObjectsFactory.get_instance().get_chat_history_mgr().user_messages(
                AppModule.WEATHER_BRIEF,
                session_id,
            )
        except Exception:
            get_logger(__name__).exception("session_id=%s place was not read from history", session_id)
            return ""
        for message in messages:
            place = self._place(message, None)
            if place:
                return place
        return ""

    def _forecast_from_place(self, place: str) -> str:
        if not place:
            return ""
        url = f"https://wttr.in/{quote(place)}?format=j1"
        request = urllib.request.Request(url, headers={"User-Agent": "daily-briefs"})
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                raw = response.read().decode()
        except (urllib.error.URLError, TimeoutError):
            get_logger(__name__).exception("place=%s weather lookup failed", place)
            return ""
        return self._forecast_from_tool(raw)

    def _weather_payload(self, raw: str) -> dict:
        start = raw.find("{")
        if start < 0:
            return {}
        try:
            payload = json.loads(raw[start:])
        except json.JSONDecodeError:
            return {}
        if not isinstance(payload, dict):
            return {}
        nested = payload.get("response")
        if isinstance(nested, str):
            inner = self._weather_payload(nested)
            if inner:
                return inner
        if isinstance(nested, dict) and nested.get("current_condition"):
            return nested
        return payload

    def _forecast_from_tool(self, raw: str) -> str:
        payload = self._weather_payload(raw)
        current = payload.get("current_condition")
        if not isinstance(current, list) or not current or not isinstance(current[0], dict):
            return ""
        row = current[0]
        temp_c = str(row.get("temp_C") or "")
        temp_f = str(row.get("temp_F") or "")
        desc = ""
        weather = row.get("weatherDesc")
        if isinstance(weather, list) and weather and isinstance(weather[0], dict):
            desc = str(weather[0].get("value") or "")
        place = ""
        nearest = payload.get("nearest_area")
        if isinstance(nearest, list) and nearest and isinstance(nearest[0], dict):
            area = nearest[0].get("areaName")
            if isinstance(area, list) and area and isinstance(area[0], dict):
                place = str(area[0].get("value") or "")
        if not temp_c and not desc:
            return ""
        where = f" in {place}" if place else ""
        sky = f" Sky: {desc}." if desc else ""
        return f"Current temperature{where}: {temp_c}°C ({temp_f}°F).{sky}"

    def _is_tool_trace(self, text: str) -> bool:
        lowered = text.lower()
        if "remote_openapi" in lowered or "remote call" in lowered or "getcurrentweather" in lowered:
            return True
        if "fetch" in lowered or "calling weather" in lowered or "call the weather" in lowered or "in progress" in lowered:
            return True
        if lowered.startswith("(") and "weather" in lowered:
            return True
        stripped = text.strip()
        return stripped.startswith("{") and "location" in stripped and "format" in stripped
