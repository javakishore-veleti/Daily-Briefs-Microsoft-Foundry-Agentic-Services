import json
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, ClassVar

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.ai.projects.models import AgentDetails, AgentVersionDetails, PromptAgentDefinition, WebSearchPreviewTool
from middleware.adapters.azure.ms_foundry.constants import AGENT_NAME_WEB_SEARCH
from middleware.common.dtos.app_config import AppConfig
from middleware.common.utils.logger_util import get_logger, log_methods
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

if TYPE_CHECKING:
    from openai import OpenAI

    from middleware.adapters.azure.ms_foundry.main_web_search import WebSearchAdapter

@log_methods
class ObjectsFactory:
    _instance: ClassVar["ObjectsFactory | None"] = None

    def __init__(self):
        self.name = "ObjectsFactory"
        self.description = "A factory that can create objects"
        self.objects = {}

    def init_ms_foundry_objects(self):
        ms_foundry_project_client = AIProjectClient(
            endpoint=AppConfig.get_instance().get_foundry_project_endpoint(),
            credential=DefaultAzureCredential()
        )
        
        api_key = AppConfig.get_instance().get_foundry_api_key()
        open_ai_client = ms_foundry_project_client.get_openai_client(
            **({"api_key": api_key} if api_key else {})
        )
        self.objects["ms_foundry_project_client"] = ms_foundry_project_client
        self.objects["open_ai_client"] = open_ai_client

        logger = get_logger(__name__)
        try:
            web_seach_agent: AgentDetails | AgentVersionDetails = ms_foundry_project_client.agents.get(
                AGENT_NAME_WEB_SEARCH
            )
            logger.info("agent_name=%s found", AGENT_NAME_WEB_SEARCH)
        except ResourceNotFoundError:
            web_seach_agent = ms_foundry_project_client.agents.create_version(
                agent_name=AGENT_NAME_WEB_SEARCH,
                definition=PromptAgentDefinition(
                    model=AppConfig.get_instance().get_model_deployment_name(),
                    instructions="You are a web search assistantagent. You are tasked with searching the web for information.",
                    tools=[WebSearchPreviewTool()],
                )
            )
            logger.info("agent_name=%s created", AGENT_NAME_WEB_SEARCH)
        except HttpResponseError:
            logger.exception("agent_name=%s unavailable via credential", AGENT_NAME_WEB_SEARCH)
            if api_key:
                self._create_agent_with_api_key(api_key)
            return

        self.objects["web_seach_agent"] = web_seach_agent

    def _create_agent_with_api_key(self, api_key: str) -> None:
        logger = get_logger(__name__)
        endpoint = AppConfig.get_instance().get_foundry_project_endpoint().rstrip("/")
        url = f"{endpoint}/agents/{AGENT_NAME_WEB_SEARCH}/versions?api-version=v1"
        definition = PromptAgentDefinition(
            model=AppConfig.get_instance().get_model_deployment_name(),
            instructions="You are a web search assistantagent. You are tasked with searching the web for information.",
            tools=[WebSearchPreviewTool()],
        )
        request = urllib.request.Request(
            url,
            data=json.dumps({"definition": definition.as_dict()}).encode(),
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                response.read()
        except urllib.error.HTTPError as error:
            if error.code == 409:
                logger.info("agent_name=%s already exists", AGENT_NAME_WEB_SEARCH)
                return
            detail = error.read().decode(errors="replace")
            logger.error(
                "agent_name=%s create failed status=%s body=%s",
                AGENT_NAME_WEB_SEARCH,
                error.code,
                detail[:500],
            )
            return
        logger.info("agent_name=%s created", AGENT_NAME_WEB_SEARCH)

    def get_web_search_agent(self) -> AgentDetails | AgentVersionDetails:
        return self.objects["web_seach_agent"]
    
    def get_open_ai_client(self) -> "OpenAI":
        return self.objects["open_ai_client"]
    
    def get_ms_foundry_project_client(self) -> AIProjectClient:
        return self.objects["ms_foundry_project_client"]
    
    def get_web_search_adapter(self) -> "WebSearchAdapter":
        from middleware.adapters.azure.ms_foundry.main_web_search import WebSearchAdapter

        if "web_search_adapter" not in self.objects:
            self.init_ms_foundry_objects()
            web_search_adapter = WebSearchAdapter()
            self.objects["web_search_adapter"] = web_search_adapter
        return self.objects["web_search_adapter"]

    @staticmethod
    def get_instance() -> "ObjectsFactory":
        if ObjectsFactory._instance is None:
            ObjectsFactory._instance = ObjectsFactory()
        return ObjectsFactory._instance
            