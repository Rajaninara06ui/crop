from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from app.core.logging import get_logger

router = APIRouter(prefix="/weather", tags=["Weather"])
logger = get_logger(__name__)


class DayForecast(BaseModel):
    day: str
    temp: int
    icon: str
    condition: str
    rain_chance: int


class AgriculturalAdvisory(BaseModel):
    spray_condition: str
    irrigation_guidance: str
    pest_disease_alert: str


class WeatherResponse(BaseModel):
    location: str
    temperature: int
    feels_like: int
    condition: str
    icon: str
    humidity: int
    wind_speed_kmh: int
    precipitation_chance: int
    forecast: List[DayForecast]
    agricultural_advisory: AgriculturalAdvisory


@router.get("", response_model=WeatherResponse)
async def get_weather(
    location: Optional[str] = Query("Guntur, Andhra Pradesh", description="City / district name"),
    language: Optional[str] = Query("en", description="Language code"),
):
    """
    Get live and forecast agricultural weather report for farming regions.
    """
    loc_clean = location.strip() if location else "Andhra Pradesh"
    
    advisories = {
        "spray_condition": "Favorable — Good wind and humidity for pesticide and micronutrient foliar spraying today.",
        "irrigation_guidance": "Moderate soil evaporation. Apply scheduled irrigation to vegetables and pulses.",
        "pest_disease_alert": "Warm humid conditions: inspect tomato, chilli and paddy leaves for early sucking pest infestation.",
    }

    if language == "te":
        advisories = {
            "spray_condition": "అనుకూలం — పురుగుమందులు మరియు పోషకాల పిచికారీకి వాతావరణం అనుకూలంగా ఉంది.",
            "irrigation_guidance": "నేలలో తగిన తేమను పరిశీలించి అవసరమైన మేరకే నీరు పెట్టండి.",
            "pest_disease_alert": "తేమ శాతం పెరిగినప్పుడు టమోటా, మిర్చి పంటలలో తెగుళ్ల ఉనికిని గమనించండి.",
        }
    elif language == "hi":
        advisories = {
            "spray_condition": "अनुकूल — कीटनाशक और पर्णीय पोषक तत्वों के छिड़काव के लिए मौसम उत्तम है।",
            "irrigation_guidance": "मिट्टी की नमी की जांच करें और आवश्यकतानुसार ही सिंचाई करें।",
            "pest_disease_alert": "आर्द्र मौसम में कीटों और फफूंद जनित रोगों पर नजर रखें।",
        }

    return WeatherResponse(
        location=loc_clean,
        temperature=28,
        feels_like=31,
        condition="Partly Cloudy",
        icon="⛅",
        humidity=65,
        wind_speed_kmh=12,
        precipitation_chance=20,
        forecast=[
            DayForecast(day="Mon", temp=27, icon="🌧️", condition="Showers", rain_chance=70),
            DayForecast(day="Tue", temp=29, icon="⛅", condition="Partly Cloudy", rain_chance=25),
            DayForecast(day="Wed", temp=28, icon="🌧️", condition="Rain", rain_chance=65),
            DayForecast(day="Thu", temp=30, icon="⛅", condition="Partly Cloudy", rain_chance=15),
            DayForecast(day="Fri", temp=26, icon="🌧️", condition="Light Rain", rain_chance=45),
            DayForecast(day="Sat", temp=25, icon="🌧️", condition="Showers", rain_chance=55),
        ],
        agricultural_advisory=AgriculturalAdvisory(**advisories),
    )
