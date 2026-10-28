from fastapi import APIRouter
from app.api.v1 import (
    auth,
    locations,
    overview,
    alerts,
    reports,
    officer,
    map as map_router,
    awareness,
    audit,
    replay,
    notifications,
    intelligence,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(locations.router)
api_router.include_router(overview.router)
api_router.include_router(alerts.router)
api_router.include_router(reports.router)
api_router.include_router(officer.router)
api_router.include_router(map_router.router)
api_router.include_router(awareness.router)
api_router.include_router(audit.router)
api_router.include_router(replay.router)
api_router.include_router(notifications.router)
api_router.include_router(intelligence.router)
