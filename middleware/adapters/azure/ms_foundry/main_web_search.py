from middleware.adapters.azure.ms_foundry.constants import AGENT_NAME_WEB_SEARCH
from middleware.adapters.azure.ms_foundry.objects_factory import ObjectsFactory
from middleware.common.dtos.web_search_dtos import WebSearchCtx
from middleware.common.utils.session_cache import SessionCache


class WebSearchAdapter:
    def __init__(self):
        self.name = "WebSearchAdapter"
        self.description = "An adapter that can search the web for information"

    def get_or_create_conversation_id(self, session_id: str, objects_factory: ObjectsFactory) -> str:
        session_cache = SessionCache.get_instance()
        session = session_cache.get(session_id)
        if not session:
            session = {"conversation_id": None}
            session_cache.set(session_id, session)
        conversation_id = session["conversation_id"]
        if isinstance(conversation_id, str) and conversation_id:
            return conversation_id

        conversation = objects_factory.get_open_ai_client().conversations.create()
        conversation_id = conversation.id
        session["conversation_id"] = conversation_id
        session_cache.set(session_id, session)
        return conversation_id

    def run(self, ctx: WebSearchCtx) -> int:
        objects_factory = ObjectsFactory.get_instance()
        conversation_id = self.get_or_create_conversation_id(ctx.req.session_id, objects_factory)

        response = objects_factory.get_open_ai_client().responses.create(
            conversation=conversation_id,
            extra_body={
                "agent": {
                    "name": AGENT_NAME_WEB_SEARCH,
                    "type": "agent_references"
                }
            },
            input = ctx.req.query
        )
        output_text = response.output_text
        ctx.resp.results["output_text"] = output_text
        ctx.resp.ctx_data["conversation_id"] = conversation_id
        return 0