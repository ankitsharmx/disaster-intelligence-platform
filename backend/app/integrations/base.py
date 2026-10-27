import time
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from shapely.geometry import Point
from geoalchemy2.shape import from_shape

from app.models.hazard import HazardObservation, DataSourceRun
from app.services.geography_service import geography_service

logger = logging.getLogger("integrations")


class HazardSource:
    """
    Unified abstract base class for all data ingestion sources.
    
    Subclasses must implement:
    - fetch(): retrieves data asynchronously from file, queue, or remote API
    - normalize(): standardizes raw schema into uniform dictionary format
    - validate(): checks constraints, data types, and reasonable thresholds
    """

    name: str = "base_source"
    hazard_type: str = "generic"
    mode: str = "demo"  # 'demo' or 'live'

    async def fetch(self) -> Any:
        """Fetch raw payload from external API or local source."""
        raise NotImplementedError("Subclasses must implement fetch()")

    def normalize(self, raw_data: Any) -> List[Dict[str, Any]]:
        """Normalize raw payload into a list of standardized record dictionaries."""
        raise NotImplementedError("Subclasses must implement normalize()")

    def validate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate records against data types, boundary ranges, and required fields."""
        raise NotImplementedError("Subclasses must implement validate()")

    async def execute_run(self, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Executes a complete ingestion lifecycle:
        1. Logs start of run in DataSourceRun
        2. Calls fetch(), normalize(), validate()
        3. Persists HazardObservation records if database session is provided
        4. Resolves district_id via GeographyService
        5. Logs final run status ('success' or 'failed') with count and duration
        """
        start_time = time.time()
        error_msg: Optional[str] = None
        validated_records: List[Dict[str, Any]] = []
        run_record: Optional[DataSourceRun] = None

        if session:
            run_record = DataSourceRun(
                source=self.name,
                mode=self.mode,
                status="running",
                retrieval_time=datetime.now(timezone.utc),
                records_count=0,
            )
            session.add(run_record)
            await session.flush()

        try:
            logger.info(f"[{self.name}][{self.mode}] Starting ingestion run...")
            raw_data = await self.fetch()
            normalized = self.normalize(raw_data)
            validated_records = self.validate(normalized)

            if session:
                for rec in validated_records:
                    lat = rec.get("latitude")
                    lon = rec.get("longitude")
                    district_id = rec.get("district_id")

                    if not district_id and lat is not None and lon is not None:
                        district_info = geography_service.resolve_district(lat, lon)
                        if district_info:
                            district_id = district_info.get("id")

                    geo_point = None
                    if lat is not None and lon is not None:
                        geo_point = from_shape(Point(lon, lat), srid=4326)

                    obs = HazardObservation(
                        hazard_type=rec.get("hazard_type", self.hazard_type),
                        values=rec.get("values", {}),
                        observed_time=rec.get("observed_time", datetime.now(timezone.utc)),
                        source=self.name,
                        district_id=district_id,
                        location=geo_point,
                        latitude=lat,
                        longitude=lon,
                    )
                    session.add(obs)

                if run_record:
                    run_record.status = "success"
                    run_record.records_count = len(validated_records)
                    run_record.metadata_json = {
                        "duration_ms": round((time.time() - start_time) * 1000, 2),
                        "record_types": [r.get("hazard_type") for r in validated_records],
                    }
                await session.flush()

            logger.info(
                f"[{self.name}][{self.mode}] Ingestion successful. Records: {len(validated_records)}"
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[{self.name}][{self.mode}] Ingestion failed: {error_msg}", exc_info=True)
            if session and run_record:
                run_record.status = "failed"
                run_record.error = error_msg
                run_record.metadata_json = {
                    "duration_ms": round((time.time() - start_time) * 1000, 2)
                }
                await session.flush()

        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "source": self.name,
            "mode": self.mode,
            "status": "success" if error_msg is None else "failed",
            "records_count": len(validated_records),
            "records": validated_records,
            "duration_ms": duration_ms,
            "error": error_msg,
        }
