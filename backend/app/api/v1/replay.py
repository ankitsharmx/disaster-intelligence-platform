from fastapi import APIRouter, HTTPException, Depends
from app.services.replay_service import replay_engine
from app.schemas.replay import (
    ReplayStartRequest,
    ReplaySpeedRequest,
    ReplayStatusResponse,
)

router = APIRouter(prefix="/replay", tags=["Demo Replay Engine"])


@router.post("/start", response_model=ReplayStatusResponse)
async def start_replay(req: ReplayStartRequest = ReplayStartRequest()):
    try:
        status = await replay_engine.start(scenario_filename=req.scenario, speed=req.speed)
        return status
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pause", response_model=ReplayStatusResponse)
def pause_replay():
    return replay_engine.pause()


@router.post("/resume", response_model=ReplayStatusResponse)
def resume_replay():
    return replay_engine.resume()


@router.post("/reset", response_model=ReplayStatusResponse)
async def reset_replay():
    return await replay_engine.reset()


@router.post("/speed", response_model=ReplayStatusResponse)
def update_replay_speed(req: ReplaySpeedRequest):
    return replay_engine.set_speed(req.speed)


@router.get("/status", response_model=ReplayStatusResponse)
def get_replay_status():
    return replay_engine.get_status()
