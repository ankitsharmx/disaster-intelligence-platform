import pytest
import asyncio
from app.services.replay_service import ReplayEngine


@pytest.mark.asyncio
async def test_replay_lifecycle():
    engine = ReplayEngine()
    
    # 1. Start scenario at 50x speed for fast unit test execution
    status = await engine.start(scenario_filename="monsoon_flood_scenario.json", speed=50.0)
    assert status["status"] == "running"
    assert status["speed"] == 50.0
    assert status["events_total"] >= 5

    # 2. Test speed change
    updated = engine.set_speed(10.0)
    assert updated["speed"] == 10.0

    # 3. Test pause
    paused = engine.pause()
    assert paused["status"] == "paused"

    # 4. Test resume
    resumed = engine.resume()
    assert resumed["status"] == "running"

    # Wait briefly for events to complete at high speed
    await asyncio.sleep(1.0)

    # 5. Test status
    cur_status = engine.get_status()
    assert cur_status["events_emitted"] > 0

    # 6. Test reset
    reset_res = await engine.reset()
    assert reset_res["status"] == "idle"
    assert reset_res["events_emitted"] == 0
