from typing import ClassVar

from pydantic import BaseModel
from dotenv import load_dotenv
import os

from middleware.common.utils.logger_util import log_methods

@log_methods
class AppConfig(BaseModel):
    _instance: ClassVar["AppConfig | None"] = None
    config: dict = {}

    def __init__(self, config: dict | None = None):
        super().__init__(config={} if config is None else config)

    @staticmethod
    def get_instance() -> "AppConfig":
        if AppConfig._instance is None:
            AppConfig._instance = AppConfig()
        return AppConfig._instance

    def load_config(self):
        load_dotenv()
        os.getenv("FOUNDRY_PROJECT_ENDPOINT")
        os.getenv("MODEL_DEPLOYMENT_NAME")
        self.config = {
            "foundry_project_endpoint": os.getenv("FOUNDRY_PROJECT_ENDPOINT"),
            "foundry_api_key": os.getenv("FOUNDRY_API_KEY", ""),
            "model_deployment_name": os.getenv("MODEL_DEPLOYMENT_NAME"),
            "text_embedding_model_name": os.getenv("TEXT_EMBEDDING_MODEL_NAME", ""),
            "hr_memory_store_name": os.getenv("HR_MEMORY_STORE_NAME", "hr-joiner-memory"),
            "hr_memory_profile_details": os.getenv(
                "HR_MEMORY_PROFILE_DETAILS",
                "food preferences, personal interests, and resumes",
            ),
            "reasoning_effort": os.getenv("REASONING_EFFORT", "minimal"),
            "api_host": os.getenv("API_HOST", "0.0.0.0"),
            "api_port": os.getenv("API_PORT", "8000"),
            "api_allowed_hosts": os.getenv("API_ALLOWED_HOSTS", "*"),
            "db_technology": os.getenv("DB_TECHNOLOGY", "mongodb"),
        }

    def get_foundry_project_endpoint(self) -> str:
        endpoint = self.config.get("foundry_project_endpoint", "")
        return endpoint if isinstance(endpoint, str) else ""

    def get_foundry_api_key(self) -> str:
        key = self.config.get("foundry_api_key", "")
        return key if isinstance(key, str) else ""

    def get_model_deployment_name(self) -> str:
        name = self.config.get("model_deployment_name", "")
        return name if isinstance(name, str) else ""

    def get_text_embedding_model_name(self) -> str:
        name = self.config.get("text_embedding_model_name", "")
        return name if isinstance(name, str) else ""

    def get_hr_memory_store_name(self) -> str:
        name = self.config.get("hr_memory_store_name", "hr-joiner-memory")
        return name.strip() if isinstance(name, str) and name.strip() else "hr-joiner-memory"

    def get_hr_memory_profile_details(self) -> str:
        details = self.config.get("hr_memory_profile_details", "")
        if not isinstance(details, str) or not details.strip():
            return "food preferences, personal interests, and resumes"
        return details.strip()

    def get_reasoning_effort(self) -> str:
        effort = self.config.get("reasoning_effort", "minimal")
        if not isinstance(effort, str):
            return "minimal"
        normalized = effort.strip().lower()
        allowed = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
        if normalized in allowed:
            return normalized
        return "minimal"

    def get_api_host(self) -> str:
        host = self.config.get("api_host", "0.0.0.0")
        return host if isinstance(host, str) and host else "0.0.0.0"

    def get_api_port(self) -> int:
        port = self.config.get("api_port", "8000")
        if isinstance(port, int):
            return port
        if isinstance(port, str) and port.isdigit():
            return int(port)
        return 8000

    def get_db_technology(self) -> str:
        technology = self.config.get("db_technology", "mongodb")
        if not isinstance(technology, str) or not technology.strip():
            return "mongodb"
        normalized = technology.strip().lower()
        if normalized in {"mongodb", "cosmosdb"}:
            return normalized
        raise RuntimeError("DB_TECHNOLOGY must be mongodb or cosmosdb")

    def get_api_allowed_hosts(self) -> list[str]:
        hosts = self.config.get("api_allowed_hosts", "*")
        if not isinstance(hosts, str) or not hosts.strip():
            return ["*"]
        return [host.strip() for host in hosts.split(",") if host.strip()]