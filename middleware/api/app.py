from typing import ClassVar

import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from middleware.api.app_bootstrap import AppBootstrap
from middleware.api.objects_factory import ObjectsFactory
from middleware.common.dtos.app_config import AppConfig
from middleware.common.utils.logger_util import log_methods


@log_methods
class App:
    _instance: ClassVar["App | None"] = None

    def __init__(self) -> None:
        self.config = AppConfig.get_instance()
        self.config.load_config()
        AppBootstrap.get_instance().init()
        self.api = FastAPI(
            title="Daily Briefs",
            docs_url="/docs",
            redoc_url="/redoc",
            openapi_url="/openapi.json",
        )
        v1 = APIRouter(prefix="/api/v1")
        v1.include_router(self._daily_briefs_router())
        self.api.include_router(v1)
        self.api.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=self.config.get_api_allowed_hosts(),
        )
        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://127.0.0.1:4200",
                "http://localhost:4200",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @staticmethod
    def get_instance() -> "App":
        if App._instance is None:
            App._instance = App()
        return App._instance

    @staticmethod
    def main() -> None:
        App.get_instance().run()

    def run(self) -> None:
        uvicorn.run(
            self.api,
            host=self.config.get_api_host(),
            port=self.config.get_api_port(),
        )

    def _daily_briefs_router(self) -> APIRouter:
        router = APIRouter(prefix="/daily-briefs", tags=["daily-briefs"])
        api_factory = ObjectsFactory.get_instance()
        web_search_api = api_factory.get_web_search_api()
        weather_info_api = api_factory.get_weather_info_api()
        chat_history_api = api_factory.get_chat_history_api()
        user_api = api_factory.get_user_api()
        router.post("/web-search")(web_search_api.web_search)
        router.post("/weather-info")(weather_info_api.weather_info)
        router.get("/chat-history")(chat_history_api.latest)
        router.post("/users/signup")(user_api.signup)
        router.post("/users/signin")(user_api.signin)
        router.post("/users/forgot-password")(user_api.forgot_password)
        router.post("/users/reset-password")(user_api.reset_password)
        router.get("/users/{user_id}")(user_api.get_profile)
        router.put("/users/{user_id}")(user_api.update_profile)
        router.delete("/users/{user_id}")(user_api.delete_profile)
        return router


app = App.get_instance().api


if __name__ == "__main__":
    App.main()
