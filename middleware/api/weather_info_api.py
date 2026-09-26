from middleware.adapters.daos.chat_history_recorder import ChatHistoryRecorder
from middleware.common.app_module import AppModule
from middleware.common.dtos.weather_info_dtos import (
    WeatherInfoApiResponse,
    WeatherInfoCtx,
    WeatherInfoReq,
    WeatherInfoResp,
)
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.facades.objects_factory import ObjectsFactory


@log_methods
class WeatherInfoApi:

    def weather_info(self, req: WeatherInfoReq) -> WeatherInfoApiResponse:
        logger = get_logger(__name__)
        logger.info("session_id=%s", req.session_id)
        ctx = WeatherInfoCtx(req=req, resp=WeatherInfoResp(results={}))
        ObjectsFactory.get_instance().get_weather_info_facade().execute(ctx)
        conversation_id = ctx.resp.ctx_data.get("conversation_id", "")
        logger.info(
            "session_id=%s conversation_id=%s input_tokens=%s output_tokens=%s",
            req.session_id,
            conversation_id,
            ctx.resp.usage.input_tokens,
            ctx.resp.usage.output_tokens,
        )
        self._record(req.session_id, req.query, conversation_id, ctx)
        return WeatherInfoApiResponse(
            output_text=ctx.resp.results.get("output_text", ""),
            conversation_id=conversation_id,
            response_id=ctx.resp.results.get("response_id", ""),
            model=ctx.resp.results.get("model", ""),
            status=ctx.resp.results.get("status", ""),
            input_tokens=ctx.resp.usage.input_tokens,
            output_tokens=ctx.resp.usage.output_tokens,
            total_tokens=ctx.resp.usage.total_tokens,
            cached_tokens=ctx.resp.usage.cached_tokens,
            reasoning_tokens=ctx.resp.usage.reasoning_tokens,
        )

    def _record(self, session_id: str, query: str, conversation_id: str, ctx: WeatherInfoCtx) -> None:
        try:
            ChatHistoryRecorder().record_turn(
                AppModule.WEATHER_BRIEF,
                session_id,
                conversation_id,
                query,
                ctx.resp.results.get("output_text", ""),
                ctx.resp.results.get("model", ""),
            )
        except Exception:
            get_logger(__name__).exception("session_id=%s chat history was not stored", session_id)
