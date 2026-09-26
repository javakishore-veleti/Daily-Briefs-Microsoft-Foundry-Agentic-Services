import json
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, ClassVar

from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.ai.projects.models import (
    AgentDetails,
    AgentVersionDetails,
    PromptAgentDefinition,
    Reasoning,
    WebSearchPreviewTool,
)
from middleware.adapters.azure.ms_foundry.constants import AGENT_NAME_WEATHER, AGENT_NAME_WEB_SEARCH
from middleware.adapters.azure.ms_foundry.weather_info.weather_open_api_def_tool import WeatherOpenApiDefTool
from middleware.common.dtos.app_config import AppConfig
from middleware.common.utils.logger_util import get_logger, log_methods
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

if TYPE_CHECKING:
    from openai import OpenAI

    from middleware.adapters.azure.ms_foundry.main_web_search import WebSearchAdapter
    from middleware.adapters.azure.ms_foundry.weather_info.main import WeatherInfoAdapter

@log_methods
class ObjectsFactory:
    _instance: ClassVar["ObjectsFactory | None"] = None

    def __init__(self):
        self.name = "ObjectsFactory"
        self.description = "A factory that can create objects"
        self.objects = {}

    def init(self) -> None:
        self.get_web_search_adapter()
        self.get_weather_info_adapter()

    def init_ms_foundry_objects(self):
        self._ensure_agent(AGENT_NAME_WEB_SEARCH, self._web_search_agent_definition(), "web_seach_agent")

    def _ensure_clients(self) -> str:
        if "open_ai_client" in self.objects:
            return AppConfig.get_instance().get_foundry_api_key()

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
        return api_key

    def _ensure_agent(self, agent_name: str, definition: PromptAgentDefinition, store_key: str) -> None:
        if store_key in self.objects:
            return

        api_key = self._ensure_clients()
        project_client = self.get_ms_foundry_project_client()
        logger = get_logger(__name__)
        try:
            agent: AgentDetails | AgentVersionDetails = project_client.agents.get(agent_name)
            if self._agent_needs_version_update(agent_name, agent):
                agent = project_client.agents.create_version(
                    agent_name=agent_name,
                    definition=definition,
                )
                logger.info("agent_name=%s version updated", agent_name)
            else:
                logger.info("agent_name=%s found", agent_name)
        except ResourceNotFoundError:
            agent = project_client.agents.create_version(
                agent_name=agent_name,
                definition=definition,
            )
            logger.info("agent_name=%s created", agent_name)
        except HttpResponseError:
            logger.exception("agent_name=%s unavailable via credential", agent_name)
            if api_key:
                self._create_agent_with_api_key(api_key, agent_name, definition)
            return

        self.objects[store_key] = agent

    def _web_search_agent_definition(self) -> PromptAgentDefinition:
        return PromptAgentDefinition(
            model=AppConfig.get_instance().get_model_deployment_name(),
            instructions="You are a web search assistantagent. You are tasked with searching the web for information.",
            tools=[WebSearchPreviewTool()],
            reasoning=Reasoning(effort=self._web_search_reasoning_effort()),
        )

    def _weather_agent_definition(self) -> PromptAgentDefinition:
        return PromptAgentDefinition(
            model=AppConfig.get_instance().get_model_deployment_name(),
            instructions=self._weather_instructions(),
            tools=[WeatherOpenApiDefTool().initialize_weather_opena_api_tool_def()],
            reasoning=Reasoning(effort=self._web_search_reasoning_effort()),
        )

    def _create_agent_with_api_key(self, api_key: str, agent_name: str, definition: PromptAgentDefinition) -> None:
        logger = get_logger(__name__)
        endpoint = AppConfig.get_instance().get_foundry_project_endpoint().rstrip("/")
        url = f"{endpoint}/agents/{agent_name}/versions?api-version=v1"
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
                logger.info("agent_name=%s already exists", agent_name)
                return
            detail = error.read().decode(errors="replace")
            logger.error(
                "agent_name=%s create failed status=%s body=%s",
                agent_name,
                error.code,
                detail[:500],
            )
            return
        logger.info("agent_name=%s created", agent_name)

    def _web_search_reasoning_effort(self) -> str:
        effort = AppConfig.get_instance().get_reasoning_effort()
        if effort == "minimal":
            return "low"
        return effort

    def _weather_instructions(self) -> str:
        return (
            "You are a weather agent. Answer only weather questions. "
            "When the user names a city, state, or country, call the weather OpenAPI tool immediately with that place and format j1. "
            "Reply with the temperature and sky conditions from the tool result. "
            "Do not ask the user to confirm a location that is already named. "
            "If the question is not about the weather, say that you only answer weather questions and ask for a city. "
            "Do not search the web, do not offer a web search, and do not answer questions about people."
        )

    def _latest_definition(self, agent: AgentDetails | AgentVersionDetails):
        versions = getattr(agent, "versions", None)
        getter = getattr(versions, "get", None)
        latest = getter("latest") if callable(getter) else None
        definition = getattr(latest, "definition", None)
        if definition is None:
            return getattr(agent, "definition", None)
        return definition

    def _agent_needs_version_update(self, agent_name: str, agent: AgentDetails | AgentVersionDetails) -> bool:
        definition = self._latest_definition(agent)
        if agent_name == AGENT_NAME_WEB_SEARCH:
            reasoning = getattr(definition, "reasoning", None)
            effort = getattr(reasoning, "effort", None)
            current = str(getattr(effort, "value", effort) or "").lower()
            return current == "minimal"
        if agent_name == AGENT_NAME_WEATHER:
            instructions = str(getattr(definition, "instructions", "") or "")
            reasoning = getattr(definition, "reasoning", None)
            effort = getattr(reasoning, "effort", None)
            current = str(getattr(effort, "value", effort) or "").lower()
            return "Reply with the temperature and sky conditions" not in instructions or current == "minimal"
        return False

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

    def get_weather_info_adapter(self) -> "WeatherInfoAdapter":
        from middleware.adapters.azure.ms_foundry.weather_info.main import WeatherInfoAdapter

        if "weather_info_adapter" not in self.objects:
            self._ensure_agent(AGENT_NAME_WEATHER, self._weather_agent_definition(), "weather_agent")
            self.objects["weather_info_adapter"] = WeatherInfoAdapter()
        return self.objects["weather_info_adapter"]

    @staticmethod
    def get_instance() -> "ObjectsFactory":
        if ObjectsFactory._instance is None:
            ObjectsFactory._instance = ObjectsFactory()
        return ObjectsFactory._instance
            