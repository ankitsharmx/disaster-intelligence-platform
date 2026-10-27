# Unified Disaster & Hazard Management Core System

A high-performance disaster management and hazard response platform redesigned around a **FastAPI** Python core, integrating real-time geospatial processing (**PostgreSQL + PostGIS**), machine learning intelligence (**scikit-learn**), asynchronous data ingestion, and scenario replay.

---

## 1. Revised Architecture Overview

| Layer | Technology | Role |
| :--- | :--- | :--- |
| **Frontend** | React / Next.js + Leaflet | Citizen reporting application & government dashboard |
| **Backend Core** | Python 3.12 + FastAPI | REST APIs, authentication, spatial querying, reports, alerts |
| **Database** | PostgreSQL 16 + PostGIS | Administrative boundaries, spatial indexing, historical records |
| **ORM & Migrations**| SQLAlchemy 2.0 (Async) + Alembic | Declarative entity modeling and version-controlled migrations |
| **Caching & Rate Limiting**| Redis 7 | High-speed response caching and API rate limiting |
| **Background Processing**| Python Workers | Periodic data ingestion, scenario playback, alert distribution |
| **Intelligence Module**| scikit-learn + Shapely | Risk rules, TF-IDF duplicate report detection, confidence scoring |
| **Deployment** | Docker Compose | Local multi-service orchestration |

---

## 2. Directory Layout & Module Responsibilities

```
Cap/
├── docker-compose.yml              # Multi-container orchestration (api, db, redis, worker)
├── requirements.txt                # Unified root Python dependency reference
├── pytest.ini                      # Pytest runner configuration
├── backend/
│   ├── Dockerfile                  # Container definition with GDAL, GEOS, PROJ & Python
│   ├── requirements.txt            # Pinned backend libraries
│   ├── alembic.ini                 # Migration tool configuration
│   ├── migrations/                 # Version-controlled schema migrations
│   │   ├── env.py                  # Dynamic database URL & model registration
│   │   └── versions/               # Auto & manual migration scripts
│   ├── app/
│   │   ├── main.py                 # FastAPI application factory, CORS, lifespan
│   │   ├── core/
│   │   │   ├── config.py           # Pydantic Settings management
│   │   │   └── security.py         # Password hashing & JWT token issuance
│   │   ├── db/
│   │   │   ├── base.py             # SQLAlchemy DeclarativeBase
│   │   │   ├── session.py          # Async engine & sessionmaker
│   │   │   └── init_db.py          # Seeding script for geography & demo accounts
│   │   ├── models/                 # Phase 1 entities (User, District, Alert, Report, etc.)
│   │   ├── schemas/                # Pydantic data validation schemas
│   │   ├── repositories/           # Database access abstraction
│   │   ├── services/
│   │   │   ├── geography_service.py # Coordinate-to-district resolution & Haversine distance
│   │   │   └── replay_service.py   # State-driven timeline simulation replay engine
│   │   ├── integrations/           # Unified HazardSource adapters
│   │   │   ├── base.py             # Abstract base adapter (fetch, normalize, validate)
│   │   │   ├── weather.py          # IMD Demo & Open-Meteo Live weather
│   │   │   ├── earthquake.py       # USGS Demo & Live earthquake GeoJSON
│   │   │   ├── fire.py             # MODIS / VIIRS thermal anomaly hotspots
│   │   │   └── alert_feed.py       # CAP-compliant government disaster alerts
│   │   ├── intelligence/           # Risk rules, confidence scoring, duplicate detector
│   │   └── workers/
│   │       ├── ingestion_worker.py # Periodic remote data synchronization
│   │       └── replay_worker.py    # CLI and background scenario player
│   ├── data/
│   │   ├── geo/                    # District GeoJSON, facilities, awareness content
│   │   └── scenarios/              # Replayable disaster scenarios (monsoon flood, etc.)
│   └── tests/                      # Automated test suite (17 passed)
```

---

## 3. Quickstart & Local Setup

### 3.1. Local Python Environment

```bash
# 1. Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Set PYTHONPATH to the backend directory
$env:PYTHONPATH="backend"

# 3. Copy environment configuration
Copy-Item .env.example .env
```

### 3.2. Launching Services via Docker Compose

```bash
# Starts PostGIS database, Redis, FastAPI backend, and Background Worker
docker compose up --build -d
```

---

## 4. Database Migrations & Static Data Seeding

### 4.1. Run Migrations (Alembic)
```bash
cd backend
alembic upgrade head
```

### 4.2. Seed Administrative & Geographic Records
Imports state boundaries, district polygons, emergency facilities (hospitals, shelters, police, fire), awareness guides, and default credentials:
```bash
python -m app.db.init_db
```

Default Accounts:
- **Admin**: `admin@disastermgmt.gov` / `Admin@123456`
- **Officer**: `officer_mumbai@disastermgmt.gov` / `Officer@123456` (Mumbai Suburban)
- **Citizen**: `citizen@example.com` / `Citizen@123456`

---

## 5. Geographic Resolution & Spatial Queries

The system features microsecond point-in-polygon resolution using Shapely and PostGIS:
```python
from app.services.geography_service import geography_service

# Inside Mumbai City
district = geography_service.resolve_district(lat=18.9300, lon=72.8250)
print(district["name"])  # 'Mumbai City'

# Outside supported bounds
out_of_bounds = geography_service.resolve_district(lat=28.6139, lon=77.2090)
print(out_of_bounds)     # None
```

Or via API:
```http
POST /api/v1/locations/resolve-district
Content-Type: application/json

{"latitude": 19.1190, "longitude": 72.8465}
```

---

## 6. Scenario Replay Engine

Simulates realistic disaster progression (e.g. Extreme Rainfall $\rightarrow$ River Level Rise $\rightarrow$ Citizen SOS Reports $\rightarrow$ Automated Red Alert Issuance $\rightarrow$ Shelter Activation).

### CLI Mode:
```bash
# Playback scenario at 5x speed
python -m app.workers.replay_worker --scenario monsoon_flood_scenario.json --speed 5.0
```

### API Controls:
- `POST /api/v1/replay/start` — Start playback (`{"scenario": "monsoon_flood_scenario.json", "speed": 2.0}`)
- `POST /api/v1/replay/pause` — Pause playback
- `POST /api/v1/replay/resume` — Resume playback
- `POST /api/v1/replay/reset` — Reset timeline to $t=0$
- `POST /api/v1/replay/speed` — Update multiplier dynamically (`{"speed": 10.0}`)
- `GET /api/v1/replay/status` — Live status, progress percentage, emitted events

---

## 7. Running Tests

Run the automated test suite with coverage:
```bash
$env:PYTHONPATH="backend"
pytest -v
```
All 17 tests covering adapters, geographic resolution, intelligence modules, replay lifecycle, and API endpoints are verified and passing.
