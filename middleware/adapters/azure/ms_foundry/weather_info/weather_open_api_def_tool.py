import json
from pathlib import Path

from azure.ai.projects.models import OpenApiAnonymousAuthDetails, OpenApiFunctionDefinition, OpenApiTool
from middleware.common.utils.logger_util import log_methods


@log_methods
class WeatherOpenApiDefTool:
    def __init__(self):
        self.name = "WeatherOpenApiTool"
        self.description = "A tool that can get weather information from the open api"

    def initialize_weather_opena_api_tool_def(self) -> OpenApiTool:
        spec_path = Path(__file__).with_name("weather_openapi.json")
        with spec_path.open(encoding="utf-8") as spec_file:
            openapi_weather = json.load(spec_file)
        return OpenApiTool(
            openapi=OpenApiFunctionDefinition(
                name="weather",
                spec=openapi_weather,
                auth=OpenApiAnonymousAuthDetails(),
            )
        )
