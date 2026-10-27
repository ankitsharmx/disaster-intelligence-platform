import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, List, Dict
import httpx

from app.integrations.base import HazardSource

DATA_DIR = Path(__file__).resolve().parent / "data"


class EarthquakeDemoSource(HazardSource):
    name = "usgs_earthquake_demo"
    hazard_type = "earthquake"
    mode = "demo"

    def __init__(self, file_path: str = "earthquake_demo.json"):
        self.file_path = DATA_DIR / file_path

    async def fetch(self) -> Any:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Earthquake demo dataset not found: {self.file_path}")
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
                "hazard_type": "earthquake",
                "event_id": item.get("event_id"),
                "location_name": item.get("place"),
                "latitude": float(item["latitude"]),
                "longitude": float(item["longitude"]),
                "observed_time": obs_dt,
                "values": {
                    "magnitude": float(item.get("magnitude", 0.0)),
                    "magnitude_type": item.get("magnitude_type", "ml"),
                    "depth_km": float(item.get("depth_km", 10.0)),
                    "status": item.get("status", "reviewed"),
                    "tsunami_alert": bool(item.get("tsunami_alert", False)),
                },
            })
        return normalized

    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        valid = []
        for r in records:
            mag = r.get("values", {}).get("magnitude", 0.0)
            lat = r.get("latitude")
            lon = r.get("longitude")
            if -90 <= lat <= 90 and -180 <= lon <= 180 and 0.0 <= mag <= 10.0:
                valid.append(r)
        return valid


class EarthquakeLiveSource(HazardSource):
    name = "usgs_earthquake_live"
    hazard_type = "earthquake"
    mode = "live"

    async def fetch(self) -> Any:
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        normalized = []
        for feature in raw_data.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [0, 0, 0])
            
            # USGS format: [lon, lat, depth]
            lon = coords[0]
            lat = coords[1]
            depth = coords[2] if len(coords) > 2 else 0.0

            time_ms = props.get("time")
            if time_ms:
                obs_dt = datetime.fromtimestamp(time_ms / 1000.0, tz=timezone.utc)
            else:
                obs_dt = datetime.now(timezone.utc)

            normalized.append({
                "hazard_type": "earthquake",
                "event_id": feature.get("id"),
                "location_name": props.get("place", "Unknown Location"),
                "latitude": float(lat),
                "longitude": float(lon),
                "observed_time": obs_dt,
                "values": {
                    "magnitude": float(props.get("mag", 0.0) or 0.0),
                    "magnitude_type": props.get("magType", "ml"),
                    "depth_km": float(depth),
                    "title": props.get("title"),
                    "source": "USGS Live GeoJSON",
                },
            })
        return normalized

    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        valid = []
        for r in records:
            mag = r.get("values", {}).get("magnitude", 0.0)
            lat = r.get("latitude")
            lon = r.get("longitude")
            if -90 <= lat <= 90 and -180 <= lon <= 180 and mag >= 0.0:
                valid.append(r)
        return valid
