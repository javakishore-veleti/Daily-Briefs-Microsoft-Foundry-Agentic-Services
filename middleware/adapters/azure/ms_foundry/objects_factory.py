from typing import TYPE_CHECKING, ClassVar

from azure.ai.projects.models import AgentVersionDetails, PromptAgentDefinition, WebSearchPreviewTool
from middleware.adapters.azure.ms_foundry.constants import AGENT_NAME_WEB_SEARCH
from middleware.common.dtos.app_config import AppConfig
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

if TYPE_CHECKING:
    from openai import OpenAI

    from middleware.adapters.azure.ms_foundry.main_web_search import WebSearchAdapter

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
        
        open_ai_client = ms_foundry_project_client.get_openai_client()

        web_seach_agent:AgentVersionDetails = ms_foundry_project_client.agents.create_version(
            agent_name=AGENT_NAME_WEB_SEARCH,
            definition=PromptAgentDefinition(
                model=AppConfig.get_instance().get_model_deployment_name(),
                instructions="You are a web search assistantagent. You are tasked with searching the web for information.",
                tools=[WebSearchPreviewTool()],
            )
        )

        self.objects["ms_foundry_project_client"] = ms_foundry_project_client
        self.objects["open_ai_client"] = open_ai_client
        self.objects["web_seach_agent"] = web_seach_agent

    def get_web_search_agent(self) -> AgentVersionDetails:
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
            