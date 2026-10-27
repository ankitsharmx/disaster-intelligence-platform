import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, List, Dict

from app.integrations.base import HazardSource

DATA_DIR = Path(__file__).resolve().parent / "data"


class FireDemoSource(HazardSource):
    name = "firms_thermal_demo"
    hazard_type = "fire"
    mode = "demo"

    def __init__(self, file_path: str = "fire_demo.json"):
        self.file_path = DATA_DIR / file_path

    async def fetch(self) -> Any:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Fire demo dataset not found: {self.file_path}")
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
                "hazard_type": "fire",
                "hotspot_id": item.get("hotspot_id"),
                "latitude": float(item["latitude"]),
                "longitude": float(item["longitude"]),
                "observed_time": obs_dt,
                "values": {
                    "brightness_kelvin": float(item.get("brightness_kelvin", 300.0)),
                    "confidence_pct": int(item.get("confidence_pct", 50)),
                    "frp_mw": float(item.get("frp_mw", 0.0)),
                    "satellite": item.get("satellite", "MODIS"),
                    "probable_cause": item.get("probable_cause", "Thermal Anomaly"),
                },
            })
        return normalized

    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        valid = []
        for r in records:
            vals = r.get("values", {})
            conf = vals.get("confidence_pct", 0)
            lat = r.get("latitude")
            lon = r.get("longitude")
            if -90 <= lat <= 90 and -180 <= lon <= 180 and 0 <= conf <= 100:
                valid.append(r)
        return valid
