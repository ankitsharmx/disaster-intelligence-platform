from fastapi import APIRouter
from app.api.v1 import (
    auth,
    locations,
    alerts,
    reports,
    officer,
    map as map_router,
    awareness,
    replay,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(locations.router)
api_router.include_router(alerts.router)
api_router.include_router(reports.router)
api_router.include_router(officer.router)
api_router.include_router(map_router.router)
api_router.include_router(awareness.router)
api_router.include_router(replay.router)
