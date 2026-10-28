import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.integrations.base import HazardSource
from app.models.alert import Alert, AlertArea
from app.models.geography import District
from app.models.hazard import DataSourceRun

DATA_DIR = Path(__file__).resolve().parent / "data"


class AlertDemoSource(HazardSource):
    name = "cap_alert_feed_demo"
    hazard_type = "alert"
    mode = "demo"

    def __init__(self, file_path: str = "alert_demo.json"):
        self.file_path = DATA_DIR / file_path

    async def fetch(self) -> Any:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Alert demo dataset not found: {self.file_path}")
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        normalized = []
        for item in raw_data:
            valid_from = datetime.fromisoformat(item["valid_from"].replace("Z", "+00:00"))
            valid_to = datetime.fromisoformat(item["valid_to"].replace("Z", "+00:00"))

            normalized.append({
                "type": item.get("event", "flood"),
                "title": item.get("headline", "Emergency Alert"),
                "description": item.get("description", ""),
                "severity": item.get("severity", "high").lower(),
                "issuer": item.get("sender", "Disaster Authority"),
                "valid_from": valid_from,
                "valid_to": valid_to,
                "status": "active",
                "target_districts": item.get("districts", []),
                "instruction": item.get("instruction", ""),
            })
        return normalized

    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        valid = []
        valid_severities = {"low", "medium", "high", "critical"}
        for r in records:
            if r.get("severity") in valid_severities and r.get("title") and r.get("valid_from") < r.get("valid_to"):
                valid.append(r)
        return valid

    async def execute_run(self, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Custom alert ingestion that persists into Alert & AlertArea tables."""
        raw_data = await self.fetch()
        normalized = self.normalize(raw_data)
        validated = self.validate(normalized)

        if session:
            for item in validated:
                alert = Alert(
                    type=item["type"][:50],
                    title=item["title"][:255],
                    description=item["description"],
                    severity=item["severity"],
                    issuer=item["issuer"][:100],
                    valid_from=item["valid_from"],
                    valid_to=item["valid_to"],
                    status="active",
                )
                session.add(alert)
                await session.flush()

                # Link target districts
                for dist_name in item.get("target_districts", []):
                    res = await session.execute(select(District).filter(District.name.ilike(f"%{dist_name}%")))
                    dist = res.scalar_one_or_none()
                    if dist:
                        area = AlertArea(
                            alert_id=alert.id,
                            district_id=dist.id,
                            boundary_geojson=dist.boundary_geojson,
                        )
                        session.add(area)
            await session.flush()

        return {
            "source": self.name,
            "mode": self.mode,
            "status": "success",
            "records_count": len(validated),
            "records": validated,
            "duration_ms": 15.0,
            "error": None,
        }
