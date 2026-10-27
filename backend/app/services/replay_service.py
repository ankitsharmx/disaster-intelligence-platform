import asyncio
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from shapely.geometry import Point
from geoalchemy2.shape import from_shape

from app.db.session import AsyncSessionLocal
from app.models.hazard import HazardObservation
from app.models.report import CitizenReport
from app.models.alert import Alert, AlertArea
from app.models.audit import AuditEvent
from app.models.geography import District, Facility
from app.services.geography_service import geography_service
from app.intelligence.scoring import ConfidenceScorer
from app.intelligence.duplicate_detector import duplicate_detector
from sqlalchemy import select

logger = logging.getLogger("replay_service")

SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "data" / "scenarios"


class ReplayEngine:
    """
    Simulation & Replay Engine that reads timeline scenario files and emits
    disaster events into the database and live notification stream.
    """

    def __init__(self):
        self.status: str = "idle"  # idle, running, paused, completed, stopped
        self.speed: float = 1.0
        self.scenario_data: Optional[Dict[str, Any]] = None
        self.current_offset: float = 0.0
        self.total_duration: float = 0.0
        self.events_emitted_count: int = 0
        self.emitted_history: List[Dict[str, Any]] = []
        self._task: Optional[asyncio.Task] = None
        self._pause_event: asyncio.Event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        self._stop_requested: bool = False

    def load_scenario(self, scenario_filename: str = "monsoon_flood_scenario.json") -> Dict[str, Any]:
        path = SCENARIOS_DIR / scenario_filename
        if not path.exists():
            raise FileNotFoundError(f"Scenario file not found at {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.scenario_data = data
        self.total_duration = float(data.get("duration_seconds", 30))
        return data

    async def start(self, scenario_filename: str = "monsoon_flood_scenario.json", speed: float = 1.0) -> Dict[str, Any]:
        """Start or restart a scenario replay."""
        await self.reset()
        self.load_scenario(scenario_filename)
        self.speed = max(0.1, min(100.0, speed))
        self.status = "running"
        self._stop_requested = False
        self._pause_event.set()
        
        # Launch background loop
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Replay started: {self.scenario_data.get('name')} at {self.speed}x speed.")
        return self.get_status()

    def pause(self) -> Dict[str, Any]:
        """Pause playback."""
        if self.status == "running":
            self.status = "paused"
            self._pause_event.clear()
            logger.info("Replay paused.")
        return self.get_status()

    def resume(self) -> Dict[str, Any]:
        """Resume playback."""
        if self.status == "paused":
            self.status = "running"
            self._pause_event.set()
            logger.info("Replay resumed.")
        return self.get_status()

    def set_speed(self, speed: float) -> Dict[str, Any]:
        """Dynamically adjust speed multiplier (0.1x to 100x)."""
        self.speed = max(0.1, min(100.0, float(speed)))
        logger.info(f"Replay speed updated to {self.speed}x.")
        return self.get_status()

    async def reset(self) -> Dict[str, Any]:
        """Stop current scenario and reset timeline counters."""
        self._stop_requested = True
        self._pause_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.status = "idle"
        self.current_offset = 0.0
        self.events_emitted_count = 0
        self.emitted_history = []
        self._task = None
        logger.info("Replay reset.")
        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "speed": self.speed,
            "scenario_id": self.scenario_data.get("scenario_id") if self.scenario_data else None,
            "scenario_name": self.scenario_data.get("name") if self.scenario_data else None,
            "current_offset_seconds": round(self.current_offset, 2),
            "total_duration_seconds": self.total_duration,
            "progress_percent": round((self.current_offset / max(1.0, self.total_duration)) * 100, 1),
            "events_total": len(self.scenario_data.get("events", [])) if self.scenario_data else 0,
            "events_emitted": self.events_emitted_count,
            "last_event": self.emitted_history[-1] if self.emitted_history else None,
        }

    async def _run_loop(self):
        """Asynchronous playback loop honoring timeline offsets and speed."""
        try:
            events = sorted(self.scenario_data.get("events", []), key=lambda x: x["time_offset_seconds"])
            last_event_time = 0.0

            for ev in events:
                target_time = float(ev["time_offset_seconds"])
                delta_time = target_time - last_event_time

                # Sleep corresponding real-time interval scaled by speed multiplier
                if delta_time > 0:
                    scaled_sleep = delta_time / self.speed
                    elapsed = 0.0
                    step_interval = 0.1
                    while elapsed < scaled_sleep:
                        if self._stop_requested:
                            return
                        await self._pause_event.wait()
                        await asyncio.sleep(step_interval)
                        elapsed += step_interval
                        self.current_offset = min(self.total_duration, last_event_time + (elapsed * self.speed))

                if self._stop_requested:
                    return

                # Emit event
                await self._emit_event(ev)
                self.events_emitted_count += 1
                last_event_time = target_time
                self.current_offset = target_time

            # Finish remaining duration if any
            if self.current_offset < self.total_duration:
                rem = (self.total_duration - self.current_offset) / self.speed
                await asyncio.sleep(rem)
                self.current_offset = self.total_duration

            self.status = "completed"
            logger.info("Scenario replay completed successfully.")

        except asyncio.CancelledError:
            self.status = "stopped"
        except Exception as e:
            logger.error(f"Error in replay loop: {e}", exc_info=True)
            self.status = "error"

    async def _emit_event(self, event_spec: Dict[str, Any]):
        """Dispatches an event to the database and registers audit event."""
        etype = event_spec.get("event_type")
        edata = event_spec.get("data", {})
        now = datetime.now(timezone.utc)
        record_id = None

        try:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    if etype == "hazard_observation":
                        lat = edata.get("latitude")
                        lon = edata.get("longitude")
                        dist_info = geography_service.resolve_district(lat, lon) if lat and lon else None
                        dist_id = dist_info.get("id") if dist_info else None

                        geo_pt = from_shape(Point(lon, lat), srid=4326) if lat and lon else None
                        obs = HazardObservation(
                            hazard_type=edata.get("hazard_type", "general"),
                            values=edata.get("values", {}),
                            observed_time=now,
                            source=edata.get("source", "replay_engine"),
                            district_id=dist_id,
                            location=geo_pt,
                            latitude=lat,
                            longitude=lon,
                        )
                        session.add(obs)
                        await session.flush()
                        record_id = obs.id

                    elif etype == "citizen_report":
                        lat = edata.get("latitude")
                        lon = edata.get("longitude")
                        dist_info = geography_service.resolve_district(lat, lon) if lat and lon else None
                        dist_id = dist_info.get("id") if dist_info else None

                        score = ConfidenceScorer.calculate_score(edata.get("description", ""))
                        geo_pt = from_shape(Point(lon, lat), srid=4326) if lat and lon else None

                        rep = CitizenReport(
                            type=edata.get("type", "flood"),
                            description=edata.get("description", ""),
                            location=geo_pt,
                            latitude=lat,
                            longitude=lon,
                            district_id=dist_id,
                            status=edata.get("status", "submitted"),
                            confidence_score=score,
                        )
                        session.add(rep)
                        await session.flush()
                        record_id = rep.id

                    elif etype == "alert":
                        alert = Alert(
                            type=edata.get("type", "flood"),
                            title=edata.get("title", "Emergency Alert"),
                            description=edata.get("description", ""),
                            severity=edata.get("severity", "critical"),
                            issuer=edata.get("issuer", "Replay Simulation"),
                            valid_from=now,
                            valid_to=now + timedelta(hours=edata.get("validity_hours", 24)),
                            status="active",
                        )
                        session.add(alert)
                        await session.flush()
                        record_id = alert.id

                        # Link districts
                        for dname in edata.get("target_district_names", []):
                            q = await session.execute(select(District).filter(District.name.ilike(f"%{dname}%")))
                            dist = q.scalar_one_or_none()
                            if dist:
                                area = AlertArea(
                                    alert_id=alert.id,
                                    district_id=dist.id,
                                    boundary_geojson=dist.boundary_geojson,
                                )
                                session.add(area)
                        await session.flush()

                    elif etype == "facility_update":
                        fac_name = edata.get("facility_name")
                        q = await session.execute(select(Facility).filter(Facility.name.ilike(f"%{fac_name}%")))
                        fac = q.scalar_one_or_none()
                        if fac:
                            fac.details = {**(fac.details or {}), **edata}
                            record_id = fac.id

                    # Audit trail
                    audit = AuditEvent(
                        actor="replay_engine",
                        action=f"replay_emitted_{etype}",
                        affected_record=f"{etype}:{record_id}",
                        details={"event": etype, "offset_sec": event_spec.get("time_offset_seconds")},
                    )
                    session.add(audit)

        except Exception as e:
            logger.warning(f"Failed to persist replay event to database (running in mock/offline mode): {e}")

        history_item = {
            "time_offset_seconds": event_spec.get("time_offset_seconds"),
            "event_type": etype,
            "record_id": record_id,
            "emitted_at": now.isoformat(),
            "data": edata,
        }
        self.emitted_history.append(history_item)
        logger.info(f"[Replay Event] Emitted {etype} at offset {event_spec.get('time_offset_seconds')}s.")


replay_engine = ReplayEngine()
