import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, List, Dict
import httpx

from app.integrations.base import HazardSource

DATA_DIR = Path(__file__).resolve().parent / "data"


class WeatherDemoSource(HazardSource):
    name = "imd_weather_demo"
    hazard_type = "rainfall"
    mode = "demo"

    def __init__(self, file_path: str = "weather_demo.json"):
        self.file_path = DATA_DIR / file_path

    async def fetch(self) -> Any:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Weather demo dataset not found: {self.file_path}")
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw_data:
            dt_str = item.get("observed_at")
            if dt_str:
                obs_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            else:
                obs_dt = datetime.now(timezone.utc)

            normalized.append({
                "hazard_type": "rainfall",
                "station_id": item.get("station_id"),
                "location_name": item.get("location_name"),
                "latitude": float(item["latitude"]),
                "longitude": float(item["longitude"]),
                "observed_time": obs_dt,
                "values": {
                    "rainfall_1h_mm": float(item.get("rainfall_1h_mm", 0.0)),
                    "rainfall_24h_mm": float(item.get("rainfall_24h_mm", 0.0)),
                    "temperature_c": float(item.get("temperature_c", 0.0)),
                    "humidity_pct": float(item.get("humidity_pct", 0.0)),
                    "wind_speed_kmh": float(item.get("wind_speed_kmh", 0.0)),
                    "condition": item.get("condition", "Heavy Rain"),
                },
            })
        return normalized

    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        valid = []
        for r in records:
            vals = r.get("values", {})
            r1h = vals.get("rainfall_1h_mm", 0.0)
            lat = r.get("latitude")
            lon = r.get("longitude")

            # Basic physical bounds checks
            if -90 <= lat <= 90 and -180 <= lon <= 180 and 0 <= r1h <= 600:
                valid.append(r)
        return valid


class WeatherLiveSource(HazardSource):
    name = "open_meteo_weather_live"
    hazard_type = "rainfall"
    mode = "live"

    def __init__(self, lat: float = 19.0760, lon: float = 72.8777, location_name: str = "Mumbai Regional Hub"):
        self.lat = lat
        self.lon = lon
        self.location_name = location_name

    async def fetch(self) -> Any:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={self.lat}&longitude={self.lon}&"
            f"current=temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m&timezone=auto"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        current = raw_data.get("current", {})
        time_str = current.get("time")
        if time_str:
            obs_dt = datetime.fromisoformat(time_str)
            if obs_dt.tzinfo is None:
                obs_dt = obs_dt.replace(tzinfo=timezone.utc)
        else:
            obs_dt = datetime.now(timezone.utc)

        precip = float(current.get("precipitation", 0.0))
        temp = float(current.get("temperature_2m", 0.0))
        humidity = float(current.get("relative_humidity_2m", 0.0))
        wind = float(current.get("wind_speed_10m", 0.0))

        record = {
            "hazard_type": "rainfall",
            "station_id": "OPEN_METEO_LIVE",
            "location_name": self.location_name,
            "latitude": float(raw_data.get("latitude", self.lat)),
            "longitude": float(raw_data.get("longitude", self.lon)),
            "observed_time": obs_dt,
            "values": {
                "rainfall_1h_mm": precip,
                "temperature_c": temp,
                "humidity_pct": humidity,
                "wind_speed_kmh": wind,
                "source_api": "Open-Meteo",
            },
        }
        return [record]

    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        valid = []
        for r in records:
            lat = r.get("latitude")
            lon = r.get("longitude")
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                valid.append(r)
        return valid
