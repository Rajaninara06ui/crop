from __future__ import annotations
from typing import Any, Dict, Optional
import httpx
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class WeatherService:
    def __init__(self) -> None:
        self.provider = settings.WEATHER_PROVIDER
        self.api_key = settings.WEATHER_API_KEY

    async def get_weather(self, location: str) -> Optional[Dict[str, Any]]:
        if not self.api_key or not self.provider:
            return None
        try:
            if self.provider.lower() == "openweather":
                url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={self.api_key}&units=metric"
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        return {
                            "temperature": data["main"]["temp"],
                            "humidity": data["main"]["humidity"],
                            "description": data["weather"][0]["description"],
                            "wind_speed": data["wind"]["speed"],
                            "location": location,
                        }
        except Exception as exc:
            logger.warning("Weather API lookup failed for '%s': %s", location, exc)
        return None
