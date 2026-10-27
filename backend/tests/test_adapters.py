import pytest
from app.integrations.weather import WeatherDemoSource, WeatherLiveSource
from app.integrations.earthquake import EarthquakeDemoSource
from app.integrations.fire import FireDemoSource
from app.integrations.alert_feed import AlertDemoSource


@pytest.mark.asyncio
async def test_weather_demo_adapter():
    source = WeatherDemoSource()
    run_res = await source.execute_run(session=None)
    assert run_res["status"] == "success"
    assert run_res["records_count"] >= 3
    first = run_res["records"][0]
    assert first["hazard_type"] == "rainfall"
    assert "rainfall_1h_mm" in first["values"]
    assert first["values"]["rainfall_1h_mm"] > 0


@pytest.mark.asyncio
async def test_earthquake_demo_adapter():
    source = EarthquakeDemoSource()
    run_res = await source.execute_run(session=None)
    assert run_res["status"] == "success"
    assert run_res["records_count"] >= 2
    first = run_res["records"][0]
    assert first["hazard_type"] == "earthquake"
    assert first["values"]["magnitude"] > 0


@pytest.mark.asyncio
async def test_fire_demo_adapter():
    source = FireDemoSource()
    run_res = await source.execute_run(session=None)
    assert run_res["status"] == "success"
    assert run_res["records_count"] >= 2
    first = run_res["records"][0]
    assert first["hazard_type"] == "fire"
    assert first["values"]["brightness_kelvin"] > 300


@pytest.mark.asyncio
async def test_alert_demo_adapter():
    source = AlertDemoSource()
    run_res = await source.execute_run(session=None)
    assert run_res["status"] == "success"
    assert run_res["records_count"] >= 1
    first = run_res["records"][0]
    assert first["severity"] == "critical"
    assert len(first["target_districts"]) > 0
