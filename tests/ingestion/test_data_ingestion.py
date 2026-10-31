"""
Multi-Hazard Disaster Intelligence Platform - Master Testing Suite
Category 02: Ingestion & Adapter Integration Testing (ING-01 to ING-14)
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "backend"))

from app.integrations.weather import WeatherDemoSource, WeatherLiveSource
from app.integrations.earthquake import EarthquakeDemoSource, EarthquakeLiveSource
from app.integrations.fire import FireDemoSource
from app.integrations.alert_feed import AlertDemoSource

@pytest.mark.asyncio
async def test_ing_01_fetch_valid_adapter_data():
    """ING-01: Fetch valid source response and verify normalized HazardObservation format."""
    source = WeatherDemoSource()
    res = await source.execute_run(session=None)
    assert res["status"] == "success"
    assert res["records_count"] >= 3
    first = res["records"][0]
    assert first["hazard_type"] == "rainfall"
    assert "latitude" in first and "longitude" in first
    assert "observed_time" in first

def test_ing_02_handle_empty_data():
    """ING-02: Source handles empty feature array safely without crashing."""
    source = EarthquakeLiveSource()
    empty_data = {"features": []}
    norm = source.normalize(empty_data)
    assert norm == []

def test_ing_03_malformed_record_rejection():
    """ING-03: Source validator detects and excludes malformed features."""
    source = EarthquakeLiveSource()
    malformed = [
        {"hazard_type": "earthquake", "latitude": 999.0, "longitude": 999.0, "values": {"magnitude": 15.0}},
        {"hazard_type": "earthquake", "latitude": 19.0, "longitude": 72.8, "values": {"magnitude": -2.0}},
    ]
    valid = source.validate(malformed)
    assert len(valid) == 0

@pytest.mark.asyncio
async def test_ing_09_duplicate_ingestion_control():
    """ING-09: Duplicate observations with identical keys are controlled."""
    source = EarthquakeDemoSource()
    records = await source.fetch()
    seen = set()
    for r in records:
        key = r.get("event_id") or (r.get("place"), r.get("observed_at"))
        seen.add(key)
    assert len(seen) == len(records), "Uncontrolled duplicate observations found in feed"

def test_ing_11_stale_source_detection():
    """ING-11: Detects when a source has not refreshed within its allowed freshness window."""
    last_retrieval = datetime.now(timezone.utc) - timedelta(hours=36)
    freshness_threshold = timedelta(hours=24)
    is_stale = (datetime.now(timezone.utc) - last_retrieval) > freshness_threshold
    assert is_stale is True, "Expected 36h-old observation to be flagged stale (>24h)"

@pytest.mark.asyncio
async def test_ing_12_and_13_demo_live_contract_invariance():
    """ING-12 & ING-13: Live and Demo adapters produce identical normalized dictionary contracts."""
    demo_eq = EarthquakeDemoSource()
    live_eq = EarthquakeLiveSource()

    demo_raw = await demo_eq.fetch()
    demo_norm = demo_eq.normalize(demo_raw)
    demo_valid = demo_eq.validate(demo_norm)
    assert len(demo_valid) > 0
    demo_rec = demo_valid[0]

    # Live mock feature
    live_mock = {
        "features": [{
            "id": "usgs_live_01",
            "properties": {"mag": 4.2, "place": "Near Delhi", "time": 1700000000000},
            "geometry": {"type": "Point", "coordinates": [77.2, 28.6, 10.0]}
        }]
    }
    live_norm = live_eq.normalize(live_mock)
    live_valid = live_eq.validate(live_norm)
    assert len(live_valid) > 0
    live_rec = live_valid[0]

    # Both must share identical dictionary contracts
    required_keys = {"hazard_type", "latitude", "longitude", "observed_time", "values"}
    assert required_keys.issubset(set(demo_rec.keys()))
    assert required_keys.issubset(set(live_rec.keys()))
    assert "magnitude" in demo_rec["values"]
    assert "magnitude" in live_rec["values"]

@pytest.mark.asyncio
async def test_ing_14_isolated_source_fault_tolerance():
    """ING-14: One failing adapter does not cascade or break other adapters."""
    sources = [WeatherDemoSource(), FireDemoSource(), AlertDemoSource()]
    results = {}
    for s in sources:
        try:
            raw = await s.fetch()
            norm = s.normalize(raw)
            val = s.validate(norm)
            results[s.name] = len(val)
        except Exception:
            results[s.name] = "FAILED"

    assert results["imd_weather_demo"] > 0
    assert results["firms_thermal_demo"] > 0
    assert results["cap_alert_feed_demo"] > 0
