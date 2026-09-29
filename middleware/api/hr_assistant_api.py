from datetime import date

from fastapi import HTTPException

from middleware.adapters.daos.chat_history_recorder import ChatHistoryRecorder
from middleware.common.app_module import AppModule
from middleware.common.dtos.hr_assistant_dtos import (
    HrAssistantApiResponse,
    HrAssistantCtx,
    HrAssistantReq,
    HrAssistantResp,
    JoinerInfoResponse,
    JoinerListResponse,
)
from middleware.common.utils.logger_util import get_logger, log_methods
from middleware.facades.objects_factory import ObjectsFactory


@log_methods
class HrAssistantApi:
    def list_joiners(self, user_id: str, joining_date: str = "", limit: int = 10, skip: int = 0) -> JoinerListResponse:
        self._require_user(user_id)
        day = joining_date.strip() or date.today().isoformat()
        page_limit = 10 if limit < 1 else min(limit, 10)
        return ObjectsFactory.get_instance().get_hr_assistant_facade().list_joiners(day, page_limit, skip)

    def get_joiner(self, joiner_info_id: str, user_id: str) -> JoinerInfoResponse:
        self._require_user(user_id)
        joiner = ObjectsFactory.get_instance().get_hr_assistant_facade().get_joiner(joiner_info_id)
        if joiner is None:
            raise HTTPException(status_code=404, detail="Joiner was not found.")
        return joiner

    def ask(self, req: HrAssistantReq) -> HrAssistantApiResponse:
        logger = get_logger(__name__)
        logger.info("session_id=%s user_id=%s joiner_info_id=%s", req.session_id, req.user_id, req.joiner_info_id)
        self._require_user(req.user_id)
        if not req.joiner_info_id.strip():
            raise HTTPException(status_code=400, detail="joiner_info_id is required.")
        if ObjectsFactory.get_instance().get_hr_assistant_facade().get_joiner(req.joiner_info_id) is None:
            raise HTTPException(status_code=404, detail="Joiner was not found.")
        ctx = HrAssistantCtx(req=req, resp=HrAssistantResp(results={}))
        ObjectsFactory.get_instance().get_hr_assistant_facade().execute(ctx)
        conversation_id = ctx.resp.ctx_data.get("conversation_id", "")
        self._record(req, conversation_id, ctx)
        return HrAssistantApiResponse(
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

    def _require_user(self, user_id: str) -> None:
        from middleware.api.objects_factory import ObjectsFactory as ApiObjectsFactory

        ApiObjectsFactory.get_instance().get_user_api().require(user_id)

    def _record(self, req: HrAssistantReq, conversation_id: str, ctx: HrAssistantCtx) -> None:
        try:
            ChatHistoryRecorder().record_turn(
                AppModule.HR_BRIEF,
                req.session_id,
                conversation_id,
                req.query,
                ctx.resp.results.get("output_text", ""),
                ctx.resp.results.get("model", ""),
                req.user_id,
                req.joiner_info_id,
            )
        except Exception:
            get_logger(__name__).exception("session_id=%s chat history was not stored", req.session_id)
