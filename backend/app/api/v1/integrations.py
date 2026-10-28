from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.session import get_db
from app.models.hazard import DataSourceRun, HazardObservation
from app.models.user import User
from app.integrations.weather import WeatherDemoSource, WeatherLiveSource
from app.integrations.earthquake import EarthquakeDemoSource, EarthquakeLiveSource
from app.integrations.fire import FireDemoSource
from app.integrations.alert_feed import AlertDemoSource
from app.api.deps import require_officer_or_above

router = APIRouter(prefix="/integrations", tags=["Data Ingestion & Live Sources"])

AVAILABLE_SOURCES = [
    EarthquakeLiveSource(),
    WeatherLiveSource(),
    WeatherDemoSource(),
    EarthquakeDemoSource(),
    FireDemoSource(),
    AlertDemoSource(),
]


@router.get("/sources")
async def list_data_sources(db: AsyncSession = Depends(get_db)):
    """
    Returns registered data ingestion sources (both Live public feeds and Demo scenario sources),
    along with their current operational mode, latest execution status, retrieval timestamp,
    records count, and last error (if any).
    """
    sources_summary = []

    for src in AVAILABLE_SOURCES:
        # Retrieve latest run for this source
        q = (
            select(DataSourceRun)
            .filter(DataSourceRun.source == src.name)
            .order_by(desc(DataSourceRun.retrieval_time))
            .limit(1)
        )
        res = await db.execute(q)
        last_run = res.scalar_one_or_none()

        sources_summary.append({
            "source_id": src.name,
            "hazard_type": src.hazard_type,
            "mode": src.mode,
            "is_live": src.mode == "live",
            "provider": (
                "USGS Live Earthquake GeoJSON (Public API)"
                if src.name == "usgs_earthquake_live"
                else (
                    "Open-Meteo Live Weather Forecast (Public API)"
                    if src.name == "open_meteo_weather_live"
                    else "Historical Demonstration Dataset"
                )
            ),
            "requires_api_key": False,
            "last_status": last_run.status if last_run else "idle",
            "last_retrieval_time": (
                last_run.retrieval_time.isoformat() if last_run and last_run.retrieval_time else None
            ),
            "records_count": last_run.records_count if last_run else 0,
            "last_error": last_run.error if last_run else None,
            "duration_ms": last_run.metadata_json.get("duration_ms") if last_run and last_run.metadata_json else None,
        })

    return {
        "total_sources": len(sources_summary),
        "live_sources_count": len([s for s in sources_summary if s["is_live"]]),
        "demo_sources_count": len([s for s in sources_summary if not s["is_live"]]),
        "sources": sources_summary,
    }


@router.post("/sync")
async def trigger_data_sync(
    source_name: Optional[str] = Query(None, description="Optional specific source to sync (e.g. usgs_earthquake_live)"),
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers an on-demand data ingestion run:
    1. Fetches external data via adapter
    2. Validates and normalizes records
    3. Resolves geographic district boundaries
    4. Persists records to PostgreSQL HazardObservation table
    5. Records execution telemetry in DataSourceRun table
    """
    targets = AVAILABLE_SOURCES
    if source_name:
        targets = [s for s in AVAILABLE_SOURCES if s.name == source_name]
        if not targets:
            return {"error": f"Source '{source_name}' not found."}

    results = []
    for src in targets:
        run_res = await src.execute_run(session=db)
        results.append({
            "source": run_res.get("source"),
            "mode": run_res.get("mode"),
            "status": run_res.get("status"),
            "records_count": run_res.get("records_count", 0),
            "duration_ms": run_res.get("duration_ms", 0.0),
            "error": run_res.get("error"),
        })

    await db.commit()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "synced_sources": results,
    }
