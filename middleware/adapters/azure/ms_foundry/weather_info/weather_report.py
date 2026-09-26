import json
import urllib.error
import urllib.request
from datetime import datetime
from urllib.parse import quote

from middleware.common.utils.logger_util import get_logger, log_methods

_COMPASS = {
    "N": "north",
    "NNE": "north-northeast",
    "NE": "northeast",
    "ENE": "east-northeast",
    "E": "east",
    "ESE": "east-southeast",
    "SE": "southeast",
    "SSE": "south-southeast",
    "S": "south",
    "SSW": "south-southwest",
    "SW": "southwest",
    "WSW": "west-southwest",
    "W": "west",
    "WNW": "west-northwest",
    "NW": "northwest",
    "NNW": "north-northwest",
}


@log_methods
class WeatherReport:
    def __init__(self):
        self.name = "WeatherReport"
        self.description = "Current conditions and the next forecast for a place"

    def compose(self, place: str, question: str) -> str:
        located = self._locate(place)
        if located is None:
            return ""
        label, latitude, longitude, country = located
        if country == "United States":
            report = self._nws_report(label, latitude, longitude, question)
            if report:
                return report
        return self._open_meteo_report(label, latitude, longitude, question)

    def _locate(self, place: str) -> tuple[str, float, float, str] | None:
        query = place.strip()
        if not query:
            return None
        payload = self._http_json(
            "https://geocoding-api.open-meteo.com/v1/search"
            f"?name={quote(query)}&count=10&language=en&format=json"
        )
        results = payload.get("results") if isinstance(payload, dict) else None
        if not isinstance(results, list):
            return None
        lowered = query.lower()
        best: dict | None = None
        best_score = 0
        for row in results:
            if not isinstance(row, dict):
                continue
            score = 0
            name = str(row.get("name") or "").lower()
            admin = str(row.get("admin1") or "").lower()
            country = str(row.get("country") or "").lower()
            if name and name in lowered:
                score += 3
            if admin and admin in lowered:
                score += 5
            if country == "united states" and ("usa" in lowered or "united states" in lowered):
                score += 2
            elif country and country in lowered:
                score += 2
            if score > best_score:
                best = row
                best_score = score
        if best is None:
            return None
        label = str(best.get("name") or query)
        admin = str(best.get("admin1") or "")
        if admin:
            label = f"{label}, {admin}"
        return label, float(best["latitude"]), float(best["longitude"]), str(best.get("country") or "")

    def _nws_report(self, label: str, latitude: float, longitude: float, question: str) -> str:
        points = self._http_json(f"https://api.weather.gov/points/{latitude:.4f},{longitude:.4f}")
        properties = points.get("properties") if isinstance(points, dict) else None
        if not isinstance(properties, dict):
            return ""
        hourly_url = str(properties.get("forecastHourly") or "")
        daily_url = str(properties.get("forecast") or "")
        hourly = self._periods(hourly_url)
        daily = self._periods(daily_url)
        if not hourly:
            return ""
        current = hourly[0]
        temp_f = current.get("temperature")
        if not isinstance(temp_f, (int, float)):
            return ""
        temp_c = round((float(temp_f) - 32) * 5 / 9)
        sky = self._sky(str(current.get("shortForecast") or "Clear"))
        humidity = self._quantity(current.get("relativeHumidity"))
        wind_speed = str(current.get("windSpeed") or "")
        wind_direction = str(current.get("windDirection") or "")
        pop = self._quantity(current.get("probabilityOfPrecipitation"))
        intro = self._intro(question, label, sky, int(temp_f), temp_c, wind_speed, wind_direction, pop, daily)
        lines = [
            intro,
            "",
            "Current Conditions",
            f"Temperature: {int(temp_f)}°F ({temp_c}°C)",
            f"Condition: {sky}",
        ]
        if humidity is not None:
            lines.append(f"Humidity: {round(humidity)}%")
        if wind_speed and wind_direction:
            lines.append(f"Wind: {self._compass(wind_direction).capitalize()} at {wind_speed}")
        upcoming = self._upcoming(daily)
        if upcoming:
            lines.extend(["", "Upcoming Forecast", *upcoming])
        return "\n".join(lines)

    def _open_meteo_report(self, label: str, latitude: float, longitude: float, question: str) -> str:
        payload = self._http_json(
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}&longitude={longitude}"
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m"
            "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            "&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=2"
        )
        current = payload.get("current") if isinstance(payload, dict) else None
        daily = payload.get("daily") if isinstance(payload, dict) else None
        if not isinstance(current, dict) or not isinstance(current.get("temperature_2m"), (int, float)):
            return ""
        temp_f = int(round(float(current["temperature_2m"])))
        temp_c = round((temp_f - 32) * 5 / 9)
        sky = self._sky_code(current.get("weather_code"))
        humidity = current.get("relative_humidity_2m")
        wind_speed = current.get("wind_speed_10m")
        wind_text = f"{int(round(float(wind_speed)))} mph" if isinstance(wind_speed, (int, float)) else ""
        direction = self._degrees(current.get("wind_direction_10m"))
        pop = None
        if isinstance(daily, dict):
            chances = daily.get("precipitation_probability_max")
            if isinstance(chances, list) and chances and isinstance(chances[0], (int, float)):
                pop = float(chances[0])
        intro = self._intro(question, label, sky, temp_f, temp_c, wind_text, direction, pop, [])
        lines = [
            intro,
            "",
            "Current Conditions",
            f"Temperature: {temp_f}°F ({temp_c}°C)",
            f"Condition: {sky}",
        ]
        if isinstance(humidity, (int, float)):
            lines.append(f"Humidity: {round(float(humidity))}%")
        if wind_text and direction:
            lines.append(f"Wind: {self._compass(direction).capitalize()} at {wind_text}")
        upcoming = self._open_meteo_upcoming(daily)
        if upcoming:
            lines.extend(["", "Upcoming Forecast", *upcoming])
        return "\n".join(lines)

    def _intro(
        self,
        question: str,
        label: str,
        sky: str,
        temp_f: int,
        temp_c: int,
        wind_speed: str,
        wind_direction: str,
        pop: float | None,
        periods: list[dict],
    ) -> str:
        lowered = question.lower()
        asks_rain = any(word in lowered for word in ("rain", "precip", "storm", "shower", "wet"))
        if asks_rain:
            rainy = self._mentions_rain(periods) or (pop is not None and pop >= 20)
            if rainy and pop is not None:
                return f"Rain is in the forecast for {label} today, with about a {round(pop)}% chance."
            if rainy:
                return f"Rain is in the forecast for {label} today."
            return f"No rain is expected in {label} today."
        sky_text = sky.lower()
        sentence = f"The current weather in {label} is {sky_text} and around {temp_f}°F ({temp_c}°C)"
        if wind_speed and wind_direction:
            sentence += f", with {self._wind_clause(wind_speed, wind_direction)}"
        return sentence + "."

    def _upcoming(self, periods: list[dict]) -> list[str]:
        lines: list[str] = []
        index = 0
        while index < len(periods) and len(lines) < 2:
            period = periods[index]
            following = periods[index + 1] if index + 1 < len(periods) else None
            if period.get("isDaytime") and isinstance(following, dict) and not following.get("isDaytime"):
                lines.append(self._day_and_night(period, following))
                index += 2
            else:
                lines.append(self._period_line(period))
                index += 1
        return lines

    def _period_line(self, period: dict) -> str:
        temp_f = int(period.get("temperature") or 0)
        temp_c = round((temp_f - 32) * 5 / 9)
        sky = str(period.get("shortForecast") or "Clear")
        kind = "high" if period.get("isDaytime") else "low"
        return f"{self._period_label(period)}: {sky}, with a {kind} around {temp_f}°F ({temp_c}°C)."

    def _day_and_night(self, day: dict, night: dict) -> str:
        high_f = int(day.get("temperature") or 0)
        low_f = int(night.get("temperature") or 0)
        high_c = round((high_f - 32) * 5 / 9)
        low_c = round((low_f - 32) * 5 / 9)
        sky = str(day.get("shortForecast") or "Clear")
        return (
            f"{self._period_label(day)}: {sky}, with a high near {high_f}°F ({high_c}°C) "
            f"and an overnight low around {low_f}°F ({low_c}°C)."
        )

    def _period_label(self, period: dict) -> str:
        name = str(period.get("name") or "Forecast")
        if name in {"Today", "Tonight", "This Afternoon", "This Morning", "Overnight"}:
            return name
        start = str(period.get("startTime") or "")
        try:
            when = datetime.fromisoformat(start)
        except ValueError:
            return name
        return f"{name}, {when.strftime('%B')} {when.day}"

    def _open_meteo_upcoming(self, daily: object) -> list[str]:
        if not isinstance(daily, dict):
            return []
        dates = daily.get("time")
        highs = daily.get("temperature_2m_max")
        lows = daily.get("temperature_2m_min")
        codes = daily.get("weather_code")
        if not isinstance(dates, list) or not isinstance(highs, list) or not isinstance(lows, list):
            return []
        lines: list[str] = []
        for index, day in enumerate(dates[:2]):
            if index >= len(highs) or index >= len(lows):
                continue
            high_f = int(round(float(highs[index])))
            low_f = int(round(float(lows[index])))
            high_c = round((high_f - 32) * 5 / 9)
            low_c = round((low_f - 32) * 5 / 9)
            sky = self._sky_code(codes[index] if isinstance(codes, list) and index < len(codes) else None)
            try:
                when = datetime.fromisoformat(str(day))
                label = f"{when.strftime('%A, %B')} {when.day}"
            except ValueError:
                label = str(day)
            lines.append(
                f"{label}: {sky}, with a high near {high_f}°F ({high_c}°C) "
                f"and a low around {low_f}°F ({low_c}°C)."
            )
        return lines

    def _periods(self, url: str) -> list[dict]:
        if not url:
            return []
        payload = self._http_json(url)
        properties = payload.get("properties") if isinstance(payload, dict) else None
        periods = properties.get("periods") if isinstance(properties, dict) else None
        if not isinstance(periods, list):
            return []
        return [period for period in periods if isinstance(period, dict)]

    def _mentions_rain(self, periods: list[dict]) -> bool:
        text = " ".join(str(period.get("shortForecast") or "") for period in periods[:4]).lower()
        return any(word in text for word in ("rain", "shower", "storm", "drizzle"))

    def _wind_clause(self, speed: str, direction: str) -> str:
        numbers = [int(item) for item in speed.replace("mph", " ").split() if item.isdigit()]
        pace = "light winds" if numbers and max(numbers) <= 12 else "winds"
        return f"{pace} from the {self._compass(direction)} at {speed}"

    def _compass(self, direction: str) -> str:
        return _COMPASS.get(direction.upper(), direction.lower())

    def _degrees(self, value: object) -> str:
        if not isinstance(value, (int, float)):
            return ""
        names = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = int((float(value) + 11.25) / 22.5) % 16
        return names[index]

    def _sky(self, text: str) -> str:
        if text.lower() in {"clear", "fair", "sunny"}:
            return "Sunny"
        return text

    def _sky_code(self, code: object) -> str:
        return {
            0: "Sunny",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Fog",
            51: "Light drizzle",
            61: "Light rain",
            63: "Rain",
            65: "Heavy rain",
            71: "Snow",
            80: "Rain showers",
            95: "Thunderstorm",
        }.get(code, "Current conditions")

    def _quantity(self, value: object) -> float | None:
        if isinstance(value, dict) and isinstance(value.get("value"), (int, float)):
            return float(value["value"])
        return None

    def _http_json(self, url: str) -> dict:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "enterprise-briefs (local)",
                "Accept": "application/geo+json, application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            get_logger(__name__).exception("weather lookup failed")
            return {}
        return payload if isinstance(payload, dict) else {}
