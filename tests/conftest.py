import asyncio
import os
import sys
from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.compiler import compiles
from fastapi.testclient import TestClient

# Add backend directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Patch GeoAlchemy2 on SQLite so in-memory testing works without external PostGIS/SpatiaLite
from geoalchemy2.types import Geometry
import geoalchemy2.admin.dialects.sqlite as sqlite_admin

sqlite_admin.before_create = lambda *args, **kwargs: None
sqlite_admin.after_create = lambda *args, **kwargs: None
sqlite_admin.before_drop = lambda *args, **kwargs: None
sqlite_admin.after_drop = lambda *args, **kwargs: None

@compiles(Geometry, "sqlite")
def compile_geom_sqlite(type_, compiler, **kw):
    return "BLOB"

Geometry.bind_expression = lambda self, bindvalue: bindvalue
Geometry.column_expression = lambda self, col: col
Geometry.result_processor = lambda self, dialect, coltype: (lambda value: value)

from app.main import app
from app.db.base import Base
from app.db.session import get_db
import app.db.session as session_module
from app.models import State, District, Facility, User, AwarenessContent
from app.models.alert import Alert
from app.models.report import CitizenReport, ReportStatus
from app.core.security import get_password_hash
from app.core.roles import Role

# Isolated in-memory SQLite database for master test execution
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Route AsyncSessionLocal to TestSessionLocal during testing
session_module.AsyncSessionLocal = TestSessionLocal


async def init_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        async with session.begin():
            # 1. State
            state = State(id=1, name="Maharashtra", code="MH")
            session.add(state)
            await session.flush()

            # 2. Districts
            d1 = District(
                id=1,
                state_id=1,
                name="Mumbai City",
                code="MUM_CITY",
                center_lat=18.96,
                center_lon=72.83,
                boundary_geojson={"type": "Polygon", "coordinates": [[[72.8, 18.9], [72.88, 18.9], [72.88, 19.04], [72.8, 19.04], [72.8, 18.9]]]},
            )
            d2 = District(
                id=2,
                state_id=1,
                name="Mumbai Suburban",
                code="MUM_SUB",
                center_lat=19.12,
                center_lon=72.88,
                boundary_geojson={"type": "Polygon", "coordinates": [[[72.77, 19.04], [72.98, 19.04], [72.98, 19.3], [72.77, 19.3], [72.77, 19.04]]]},
            )
            d4 = District(
                id=4,
                state_id=1,
                name="Pune",
                code="PUNE",
                center_lat=18.52,
                center_lon=73.85,
                boundary_geojson={"type": "Polygon", "coordinates": [[[73.65, 18.35], [74.25, 18.35], [74.25, 18.8], [73.65, 18.8], [73.65, 18.35]]]},
            )
            session.add_all([d1, d2, d4])
            await session.flush()

            # 3. Facilities
            fac = Facility(
                id=1,
                name="Cooper Hospital",
                category="hospital",
                district_id=2,
                latitude=19.1085,
                longitude=72.8360,
                contact_number="+91-22-2620-7254",
                capacity=650,
            )
            session.add(fac)

            # 4. Awareness content
            aw1 = AwarenessContent(
                hazard="flood",
                stage="during",
                language="en",
                title="Flood Safety During Inundation",
                instructions=["Move to higher ground", "Turn off electricity"],
            )
            aw2 = AwarenessContent(
                hazard="flood",
                stage="during",
                language="hi",
                title="बाढ़ के दौरान सुरक्षा",
                instructions=["ऊंचे स्थानों पर जाएं", "बिजली बंद करें"],
            )
            aw3 = AwarenessContent(
                hazard="landslide",
                stage="during",
                language="en",
                title="Landslide Safety",
                instructions=["Evacuate immediately", "Stay away from slope base"],
            )
            aw4 = AwarenessContent(
                hazard="landslide",
                stage="during",
                language="hi",
                title="भूस्खलन सुरक्षा",
                instructions=["तुरंत बाहर निकलें", "ढलान से दूर रहें"],
            )
            aw5 = AwarenessContent(
                hazard="earthquake",
                stage="during",
                language="en",
                title="Earthquake Safety - Drop, Cover, and Hold On",
                instructions=["Drop to hands and knees", "Cover head and neck", "Hold on until shaking stops"],
            )
            aw6 = AwarenessContent(
                hazard="earthquake",
                stage="during",
                language="hi",
                title="भूकंप सुरक्षा - झुकें, ढकें और पकड़ें",
                instructions=["हाथ और घुटनों के बल झुकें", "सिर को ढकें", "कंपन रुकने तक मजबूती से पकड़े रहें"],
            )
            aw7 = AwarenessContent(
                hazard="fire",
                stage="during",
                language="en",
                title="Fire Evacuation and Safety",
                instructions=["Crawl low under smoke", "Feel doors before opening", "Call emergency services"],
            )
            aw8 = AwarenessContent(
                hazard="fire",
                stage="during",
                language="hi",
                title="आग से बचाव और सुरक्षा",
                instructions=["धुएं के नीचे झुककर चलें", "दरवाजा छूकर देखें", "आपातकालीन नंबर पर कॉल करें"],
            )
            session.add_all([aw1, aw2, aw3, aw4, aw5, aw6, aw7, aw8])

            # 5. Users for all 4 roles
            users = [
                User(
                    id=1,
                    email="admin@disastermgmt.gov",
                    full_name="System Administrator",
                    hashed_password=get_password_hash("Admin@123456"),
                    role=Role.SYSTEM_ADMIN.value,
                    assigned_district_id=None,
                    assigned_state_id=None,
                    is_active=True,
                ),
                User(
                    id=2,
                    email="state_admin_mh@disastermgmt.gov",
                    full_name="State Admin (MH)",
                    hashed_password=get_password_hash("StateAdmin@123456"),
                    role=Role.STATE_ADMIN.value,
                    assigned_district_id=None,
                    assigned_state_id=1,
                    is_active=True,
                ),
                User(
                    id=3,
                    email="officer_mumbai@disastermgmt.gov",
                    full_name="Officer Mumbai Suburban",
                    hashed_password=get_password_hash("Officer@123456"),
                    role=Role.DISTRICT_OFFICER.value,
                    assigned_district_id=2,  # Mumbai Suburban
                    assigned_state_id=1,
                    is_active=True,
                ),
                User(
                    id=4,
                    email="officer_pune@disastermgmt.gov",
                    full_name="Officer Pune",
                    hashed_password=get_password_hash("Officer@123456"),
                    role=Role.DISTRICT_OFFICER.value,
                    assigned_district_id=4,  # Pune
                    assigned_state_id=1,
                    is_active=True,
                ),
                User(
                    id=5,
                    email="citizen@example.com",
                    full_name="Aarav Sharma",
                    hashed_password=get_password_hash("Citizen@123456"),
                    role=Role.CITIZEN.value,
                    assigned_district_id=None,
                    assigned_state_id=None,
                    is_active=True,
                ),
            ]
            session.add_all(users)
            await session.flush()

            # 6. Pre-seed targeted alert for district 2
            from datetime import datetime, timezone, timedelta
            from app.models.alert import AlertArea
            now = datetime.now(timezone.utc)
            alert_d2 = Alert(
                id=1,
                type="flood",
                severity="warning",
                title="Heavy Rain Advisory",
                description="Heavy downpours expected in Mumbai Suburban",
                issuer="Regional Meteorological Centre",
                is_official=False,
                valid_from=now - timedelta(hours=1),
                valid_to=now + timedelta(days=2),
                status="active",
                created_by_user_id=3,
            )
            session.add(alert_d2)
            await session.flush()
            area1 = AlertArea(id=1, alert_id=1, district_id=2)
            session.add(area1)
            await session.flush()


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Initializes in-memory database schema and default records once per test session."""
    asyncio.run(init_test_db())
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
