from typing import ClassVar

from pydantic import BaseModel
from dotenv import load_dotenv
import os

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

    def load_config(self, config_file: str):
        load_dotenv()
        os.getenv("FOUNDRY_PROJECT_ENDPOINT")
        os.getenv("MODEL_DEPLOYMENT_NAME")
        self.config = {
            "foundry_project_endpoint": os.getenv("FOUNDRY_PROJECT_ENDPOINT"),
            "model_deployment_name": os.getenv("MODEL_DEPLOYMENT_NAME")
        }

    def get_foundry_project_endpoint(self) -> str:
        endpoint = self.config.get("foundry_project_endpoint", "")
        return endpoint if isinstance(endpoint, str) else ""

    def get_model_deployment_name(self) -> str:
        name = self.config.get("model_deployment_name", "")
        return name if isinstance(name, str) else ""