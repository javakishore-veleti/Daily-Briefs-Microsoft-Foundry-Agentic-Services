from typing import override

from middleware.adapters.azure.azure_foundry_adapter import AzureMsFoundryAppAdapter
from middleware.adapters.azure.ms_foundry.constants import AGENT_NAME_WEATHER
from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory
from middleware.common.app_exec_contants import AppExecConstants
from middleware.common.dtos.common import AppCtx
from middleware.common.dtos.weather_info_dtos import WeatherInfoReq, WeatherInfoResp
from middleware.common.utils.logger_util import get_logger, log_methods


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

        response = objects_factory.get_open_ai_client().responses.create(
            conversation=conversation_id,
            extra_body={
                "agent_reference": {
                    "name": AGENT_NAME_WEATHER,
                    "type": "agent_reference",
                }
            },
            input=ctx.req.query,
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
        ctx.resp.results["output_text"] = response.output_text
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
