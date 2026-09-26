class AppModule:
    DAILY_BRIEF = "daily-brief"
    WEATHER_BRIEF = "weather-brief"
    DAILY_BRIEFS_SEARCH = "daily-briefs-search"
    WEATHER_AGENT = "weather-agent"

    @staticmethod
    def values() -> set[str]:
        return {AppModule.DAILY_BRIEF, AppModule.WEATHER_BRIEF}

    @staticmethod
    def is_known(value: str) -> bool:
        return value in AppModule.values()

    @staticmethod
    def from_brief(brief: str) -> str:
        briefs = {
            AppModule.DAILY_BRIEFS_SEARCH: AppModule.DAILY_BRIEF,
            AppModule.WEATHER_AGENT: AppModule.WEATHER_BRIEF,
        }
        return briefs.get(brief, "")
