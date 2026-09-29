class AppModule:
    DAILY_BRIEF = "daily-brief"
    WEATHER_BRIEF = "weather-brief"
    HR_BRIEF = "hr-brief"
    DAILY_BRIEFS_SEARCH = "daily-briefs-search"
    WEATHER_AGENT = "weather-agent"
    HR_DAILY_BRIEF = "hr-daily-brief"

    @staticmethod
    def values() -> set[str]:
        return {AppModule.DAILY_BRIEF, AppModule.WEATHER_BRIEF, AppModule.HR_BRIEF}

    @staticmethod
    def is_known(value: str) -> bool:
        return value in AppModule.values()

    @staticmethod
    def from_brief(brief: str) -> str:
        briefs = {
            AppModule.DAILY_BRIEFS_SEARCH: AppModule.DAILY_BRIEF,
            AppModule.WEATHER_AGENT: AppModule.WEATHER_BRIEF,
            AppModule.HR_DAILY_BRIEF: AppModule.HR_BRIEF,
        }
        return briefs.get(brief, "")
