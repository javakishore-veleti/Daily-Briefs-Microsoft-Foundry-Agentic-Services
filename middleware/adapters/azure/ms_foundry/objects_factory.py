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
from middleware.adapters.azure.ms_foundry.constants import (
    AGENT_NAME_HR_ASSISTANT,
    AGENT_NAME_WEATHER,
    AGENT_NAME_WEB_SEARCH,
)
from middleware.adapters.azure.ms_foundry.weather_info.weather_open_api_def_tool import WeatherOpenApiDefTool
from middleware.common.dtos.app_config import AppConfig
from middleware.common.utils.logger_util import get_logger, log_methods
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

if TYPE_CHECKING:
    from openai import OpenAI

    from middleware.adapters.azure.ms_foundry.hr_assistant_agent.main import HrAssistantAdapter
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
        self.get_hr_assistant_adapter()

    def init_ms_foundry_objects(self):
        self._ensure_agent(AGENT_NAME_WEB_SEARCH, self._web_search_agent_definition(), "web_seach_agent")

    def _ensure_clients(self) -> str:
        if "open_ai_client" in self.objects:
            return AppConfig.get_instance().get_foundry_api_key()

        config = AppConfig.get_instance()
        project_endpoint = config.get_foundry_project_endpoint().rstrip("/")
        openai_base_url = f"{project_endpoint}/openai/v1"
        ms_foundry_project_client = AIProjectClient(
            endpoint=project_endpoint,
            credential=DefaultAzureCredential(),
            allow_preview=True,
        )
        api_key = config.get_foundry_api_key()
        client_kwargs = {"base_url": openai_base_url}
        if api_key:
            client_kwargs["api_key"] = api_key
        open_ai_client = ms_foundry_project_client.get_openai_client(**client_kwargs)
        get_logger(__name__).info(
            "foundry_project=%s openai_base_url=%s",
            project_endpoint,
            getattr(open_ai_client, "base_url", openai_base_url),
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

    def _configured_model(self) -> str:
        return AppConfig.get_instance().get_model_deployment_name()

    def _reasoning_for_model(self) -> Reasoning | None:
        if not self._configured_model().startswith("gpt-5"):
            return None
        return Reasoning(effort=self._web_search_reasoning_effort())

    def _prompt_definition(self, instructions: str, tools: list) -> PromptAgentDefinition:
        kwargs = {
            "model": self._configured_model(),
            "instructions": instructions,
        }
        if tools:
            kwargs["tools"] = tools
        reasoning = self._reasoning_for_model()
        if reasoning is not None:
            kwargs["reasoning"] = reasoning
        return PromptAgentDefinition(**kwargs)

    def _web_search_agent_definition(self) -> PromptAgentDefinition:
        return self._prompt_definition(
            "You are a web search assistantagent. You are tasked with searching the web for information.",
            [WebSearchPreviewTool()],
        )

    def _weather_agent_definition(self) -> PromptAgentDefinition:
        return self._prompt_definition(
            self._weather_instructions(),
            [WeatherOpenApiDefTool().initialize_weather_opena_api_tool_def()],
        )

    def _hr_assistant_agent_definition(self) -> PromptAgentDefinition:
        return self._prompt_definition(self._hr_instructions(), [])

    def _create_agent_with_api_key(self, api_key: str, agent_name: str, definition: PromptAgentDefinition) -> None:
        logger = get_logger(__name__)
        endpoint = AppConfig.get_instance().get_foundry_project_endpoint().rstrip("/")
        existing = self._agent_text_with_api_key(api_key, endpoint, agent_name)
        if self._api_key_agent_is_current(existing, definition):
            logger.info("agent_name=%s already current", agent_name)
            return
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

    def _agent_text_with_api_key(self, api_key: str, endpoint: str, agent_name: str) -> str:
        request = urllib.request.Request(
            f"{endpoint}/agents/{agent_name}?api-version=v1",
            headers={"api-key": api_key, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode(errors="replace")
        except urllib.error.URLError:
            return ""

    def _web_search_reasoning_effort(self) -> str:
        effort = AppConfig.get_instance().get_reasoning_effort()
        if effort == "minimal":
            return "low"
        return effort

    def _weather_instructions(self) -> str:
        return (
            "You are a weather agent. Answer weather questions, including follow-ups in this conversation. "
            "Follow-up weather questions use the place already named in this conversation. "
            "When a city, state, or country is known, call the weather tool for that place. "
            "Answer rain, temperature, wind, humidity, and forecast questions for that place. "
            "Ask for a city only when no place has been named in this conversation. "
            "If the question is not about the weather, say that you only answer weather questions. "
            "Do not search the web and do not answer questions about people."
        )

    def _hr_instructions(self) -> str:
        return (
            "You are an HR assistant. Answer questions about the new joiner named in this conversation. "
            "Answer resumes, personal interests, and food preferences only from the Memory context included with the question. "
            "If that Memory context does not contain the fact, say you have no memory for it yet. "
            "Follow-up questions stay on that joiner. "
            "If the question is not about that joiner, say that you only answer questions about that joiner."
        )

    def _latest_definition(self, agent: AgentDetails | AgentVersionDetails):
        versions = getattr(agent, "versions", None)
        getter = getattr(versions, "get", None)
        latest = getter("latest") if callable(getter) else None
        definition = getattr(latest, "definition", None)
        if definition is None:
            return getattr(agent, "definition", None)
        return definition

    def _published_model(self, existing: str) -> str:
        try:
            body = json.loads(existing)
        except json.JSONDecodeError:
            return ""
        versions = body.get("versions") if isinstance(body, dict) else None
        latest = versions.get("latest") if isinstance(versions, dict) else None
        definition = latest.get("definition") if isinstance(latest, dict) else None
        if not isinstance(definition, dict):
            return ""
        return str(definition.get("model") or "")

    def _api_key_agent_is_current(self, existing: str, definition: PromptAgentDefinition) -> bool:
        instructions = str(getattr(definition, "instructions", "") or "")
        if not instructions or instructions not in existing:
            return False
        return self._published_model(existing) == self._configured_model()

    def _agent_needs_version_update(self, agent_name: str, agent: AgentDetails | AgentVersionDetails) -> bool:
        definition = self._latest_definition(agent)
        published = str(getattr(definition, "model", "") or "")
        if published != self._configured_model():
            return True
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
            return "Follow-up weather questions use the place already named" not in instructions or current == "minimal"
        if agent_name == AGENT_NAME_HR_ASSISTANT:
            instructions = str(getattr(definition, "instructions", "") or "")
            return "Answer resumes, personal interests, and food preferences only from the Memory context" not in instructions
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

    def get_hr_assistant_adapter(self) -> "HrAssistantAdapter":
        from middleware.adapters.azure.ms_foundry.hr_assistant_agent.main import HrAssistantAdapter
        from middleware.adapters.azure.ms_foundry.hr_assistant_agent.memory_store import HrMemoryStore

        if "hr_assistant_adapter" not in self.objects:
            self._ensure_agent(AGENT_NAME_HR_ASSISTANT, self._hr_assistant_agent_definition(), "hr_assistant_agent")
            if "ms_foundry_project_client" in self.objects:
                HrMemoryStore().ensure(self.get_ms_foundry_project_client())
            self.objects["hr_assistant_adapter"] = HrAssistantAdapter()
        return self.objects["hr_assistant_adapter"]

    @staticmethod
    def get_instance() -> "ObjectsFactory":
        if ObjectsFactory._instance is None:
            ObjectsFactory._instance = ObjectsFactory()
        return ObjectsFactory._instance
            