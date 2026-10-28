import asyncio
import json
import logging
from pathlib import Path
from shapely.geometry import shape, Point
from geoalchemy2.shape import from_shape
from sqlalchemy import select

from app.db.session import engine, AsyncSessionLocal
from app.db.base import Base
from app.core.security import get_password_hash
from app.core.roles import Role
from app.models import (
    State,
    District,
    Facility,
    User,
    AwarenessContent,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "geo"


async def init_models():
    """Create all tables in database if not using Alembic directly."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified.")


async def seed_geography(session):
    """Seed states, districts, and facilities from static datasets."""
    # 1. States
    states_file = DATA_DIR / "states.json"
    if states_file.exists():
        with open(states_file, "r", encoding="utf-8") as f:
            states_data = json.load(f)
        for s_data in states_data:
            existing = await session.execute(select(State).filter_by(code=s_data["code"]))
            if not existing.scalar_one_or_none():
                state = State(id=s_data["id"], name=s_data["name"], code=s_data["code"])
                session.add(state)
        await session.flush()
        logger.info("States seeded.")

    # 2. Districts
    districts_file = DATA_DIR / "districts.geojson"
    if districts_file.exists():
        with open(districts_file, "r", encoding="utf-8") as f:
            districts_geojson = json.load(f)

        for feature in districts_geojson.get("features", []):
            props = feature["properties"]
            geom_data = feature["geometry"]
            existing = await session.execute(select(District).filter_by(id=props["id"]))
            if not existing.scalar_one_or_none():
                shapely_geom = shape(geom_data)
                geo_elem = from_shape(shapely_geom, srid=4326)

                district = District(
                    id=props["id"],
                    state_id=props["state_id"],
                    name=props["name"],
                    code=props.get("code"),
                    boundary=geo_elem,
                    boundary_geojson=geom_data,
                    center_lat=props.get("center_lat"),
                    center_lon=props.get("center_lon"),
                )
                session.add(district)
        await session.flush()
        logger.info("Districts seeded.")

    # 3. Facilities
    facilities_file = DATA_DIR / "facilities.json"
    if facilities_file.exists():
        with open(facilities_file, "r", encoding="utf-8") as f:
            facilities_data = json.load(f)

        for fac_data in facilities_data:
            existing = await session.execute(select(Facility).filter_by(name=fac_data["name"]))
            if not existing.scalar_one_or_none():
                pt = Point(fac_data["longitude"], fac_data["latitude"])
                geo_point = from_shape(pt, srid=4326)

                facility = Facility(
                    name=fac_data["name"],
                    category=fac_data["category"],
                    district_id=fac_data["district_id"],
                    coordinates=geo_point,
                    latitude=fac_data["latitude"],
                    longitude=fac_data["longitude"],
                    contact_number=fac_data.get("contact_number"),
                    capacity=fac_data.get("capacity"),
                    details=fac_data.get("details"),
                )
                session.add(facility)
        await session.flush()
        logger.info("Facilities seeded.")


async def seed_users(session):
    """Seed accounts representing all 4 documented roles."""
    default_users = [
        # 1. System Administrator: Global access across all states and districts
        {
            "email": "admin@disastermgmt.gov",
            "full_name": "System Administrator",
            "password": get_password_hash("Admin@123456"),
            "role": Role.SYSTEM_ADMIN.value,
            "assigned_district_id": None,
            "assigned_state_id": None,
        },
        # 2. State Administrator: State of Maharashtra (State ID 1)
        {
            "email": "state_admin_mh@disastermgmt.gov",
            "full_name": "Maharashtra State Disaster Director",
            "password": get_password_hash("StateAdmin@123456"),
            "role": Role.STATE_ADMIN.value,
            "assigned_district_id": None,
            "assigned_state_id": 1,
        },
        # 3. District Officer: Mumbai Suburban (District ID 2)
        {
            "email": "officer_mumbai@disastermgmt.gov",
            "full_name": "Disaster Response Officer (Mumbai Suburban)",
            "password": get_password_hash("Officer@123456"),
            "role": Role.DISTRICT_OFFICER.value,
            "assigned_district_id": 2,
            "assigned_state_id": 1,
        },
        # 4. District Officer: Pune (District ID 4)
        {
            "email": "officer_pune@disastermgmt.gov",
            "full_name": "Disaster Response Officer (Pune)",
            "password": get_password_hash("Officer@123456"),
            "role": Role.DISTRICT_OFFICER.value,
            "assigned_district_id": 4,
            "assigned_state_id": 1,
        },
        # 5. Citizen
        {
            "email": "citizen@example.com",
            "full_name": "Aarav Sharma",
            "password": get_password_hash("Citizen@123456"),
            "role": Role.CITIZEN.value,
            "assigned_district_id": None,
            "assigned_state_id": None,
        },
    ]

    for u_data in default_users:
        existing = await session.execute(select(User).filter_by(email=u_data["email"]))
        u = existing.scalar_one_or_none()
        if not u:
            user = User(
                email=u_data["email"],
                full_name=u_data["full_name"],
                hashed_password=u_data["password"],
                role=u_data["role"],
                assigned_district_id=u_data["assigned_district_id"],
                assigned_state_id=u_data.get("assigned_state_id"),
                is_active=True,
            )
            session.add(user)
        else:
            # Update role and assignments if existing
            u.role = u_data["role"]
            u.assigned_district_id = u_data["assigned_district_id"]
            u.assigned_state_id = u_data.get("assigned_state_id")
            session.add(u)
    await session.flush()
    logger.info("Users for all 4 roles seeded.")


async def seed_awareness(session):
    """Seed public awareness content."""
    awareness_file = DATA_DIR / "awareness.json"
    if awareness_file.exists():
        with open(awareness_file, "r", encoding="utf-8") as f:
            items = json.load(f)

        for item in items:
            existing = await session.execute(
                select(AwarenessContent).filter_by(
                    hazard=item["hazard"], stage=item["stage"], language=item["language"]
                )
            )
            if not existing.scalar_one_or_none():
                ac = AwarenessContent(
                    hazard=item["hazard"],
                    stage=item["stage"],
                    language=item["language"],
                    title=item["title"],
                    instructions=item["instructions"],
                )
                session.add(ac)
        await session.flush()
        logger.info("Awareness content seeded.")


async def main():
    logger.info("Starting database initialization and seeding...")
    await init_models()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await seed_geography(session)
            await seed_users(session)
            await seed_awareness(session)
    logger.info("Initialization and seeding complete.")


if __name__ == "__main__":
    asyncio.run(main())
