"""
OpenWeatherMap connector for the Watcher Agent.
Monitors severe weather alerts for 12 Indian metro cities.
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from ..schemas import Signal

logger = logging.getLogger(__name__)

API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

# 12 Indian cities from BLUEPRINT.md Section 7
CITIES_MONITORED = [
    ("Thiruvananthapuram", 8.5241, 76.9366, "Kerala"),
    ("Kochi", 9.9312, 76.2673, "Kerala"),
    ("Alappuzha", 9.4981, 76.3388, "Kerala"),
    ("Chennai", 13.0827, 80.2707, "Tamil Nadu"),
    ("Bengaluru", 12.9716, 77.5946, "Karnataka"),
    ("Mumbai", 19.0760, 72.8777, "Maharashtra"),
    ("Delhi", 28.6139, 77.2090, "Delhi"),
    ("Kolkata", 22.5726, 88.3639, "West Bengal"),
    ("Hyderabad", 17.3850, 78.4867, "Telangana"),
    ("Pune", 18.5204, 73.8567, "Maharashtra"),
    ("Ahmedabad", 23.0225, 72.5714, "Gujarat"),
    ("Guwahati", 26.1445, 91.7362, "Assam"),
]

# Severe weather IDs from OpenWeatherMap
# 200-232: Thunderstorm
# 502-531: Heavy rain
# 602-622: Heavy snow
SEVERE_WEATHER_IDS = set(range(200, 233)) | set(range(502, 532)) | set(range(602, 623))

# Alert thresholds
RAINFALL_THRESHOLD_MM_3H = 50
WIND_THRESHOLD_KMPH = 60


async def fetch_weather_signals() -> list[Signal]:
    """
    Fetch current weather for all monitored cities.
    Returns signals only for cities with severe conditions.
    """
    signals = []
    
    if not API_KEY:
        logger.warning("OpenWeather API key not set, skipping weather source")
        return signals
    
    async with httpx.AsyncClient(timeout=10) as client:
        for city_name, lat, lon, state in CITIES_MONITORED:
            try:
                response = await client.get(BASE_URL, params={
                    "lat": lat,
                    "lon": lon,
                    "appid": API_KEY,
                    "units": "metric",
                })
                
                if response.status_code != 200:
                    logger.warning(f"Weather API error for {city_name}: {response.status_code}")
                    continue
                
                data = response.json()
                signal = _evaluate_weather(data, city_name, lat, lon, state)
                if signal:
                    signals.append(signal)
                    
            except Exception as e:
                logger.error(f"Weather fetch failed for {city_name}: {e}")
    
    logger.info(f"Weather check complete: {len(signals)} alerts from {len(CITIES_MONITORED)} cities")
    return signals


def _evaluate_weather(
    data: dict,
    city_name: str,
    lat: float,
    lon: float,
    state: str,
) -> Optional[Signal]:
    """
    Evaluate if weather data indicates severe conditions.
    Triggers on: rainfall > 50mm/3hr OR wind > 60kmph OR severe weather ID.
    """
    weather_id = data.get("weather", [{}])[0].get("id", 0)
    weather_desc = data.get("weather", [{}])[0].get("description", "")
    
    # Rain in last 3 hours
    rain_3h = data.get("rain", {}).get("3h", 0)
    
    # Wind speed (m/s → km/h)
    wind_ms = data.get("wind", {}).get("speed", 0)
    wind_kmph = wind_ms * 3.6
    
    # Temperature
    temp = data.get("main", {}).get("temp", 0)
    humidity = data.get("main", {}).get("humidity", 0)
    
    # Check alert conditions
    is_severe = (
        weather_id in SEVERE_WEATHER_IDS
        or rain_3h > RAINFALL_THRESHOLD_MM_3H
        or wind_kmph > WIND_THRESHOLD_KMPH
    )
    
    if not is_severe:
        return None
    
    # Build alert content
    alerts = []
    if weather_id in SEVERE_WEATHER_IDS:
        alerts.append(f"Severe weather: {weather_desc} (ID: {weather_id})")
    if rain_3h > RAINFALL_THRESHOLD_MM_3H:
        alerts.append(f"Heavy rainfall: {rain_3h}mm in 3 hours")
    if wind_kmph > WIND_THRESHOLD_KMPH:
        alerts.append(f"High wind: {wind_kmph:.0f} km/h")
    
    content = f"{city_name}, {state}: {'; '.join(alerts)}. Temp: {temp}°C, Humidity: {humidity}%"
    
    logger.info(f"⚠️ Weather alert: {content}")
    
    return Signal(
        source_type="openweather",
        source_name="openweather",
        timestamp=datetime.now(timezone.utc),
        content=content,
        location_hint=f"{city_name}, {state}",
        crisis_type_hint="flood" if rain_3h > RAINFALL_THRESHOLD_MM_3H else "weather",
        raw_data={
            "city": city_name,
            "state": state,
            "lat": lat,
            "lon": lon,
            "weather_id": weather_id,
            "rain_3h": rain_3h,
            "wind_kmph": round(wind_kmph, 1),
            "temp": temp,
            "humidity": humidity,
        },
    )
