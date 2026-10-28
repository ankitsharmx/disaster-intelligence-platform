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
- **System Admin**: `admin@disastermgmt.gov` / `Admin@123456`
- **State Admin**: `state_admin_mh@disastermgmt.gov` / `StateAdmin@123456` (Maharashtra)
- **District Officer (Mumbai Suburban)**: `officer_mumbai@disastermgmt.gov` / `Officer@123456` (District ID: 2)
- **District Officer (Pune)**: `officer_pune@disastermgmt.gov` / `Officer@123456` (District ID: 4)
- **Citizen**: `citizen@example.com` / `Citizen@123456`

---

## 5. Phase 2 FastAPI Core APIs

### 5.1. Authentication & RBAC (`/api/v1/auth`)
- `POST /api/v1/auth/register` — Public registration (strictly creates `CITIZEN` role).
- `POST /api/v1/auth/provision` — Administrative provisioning of `DISTRICT_OFFICER` and `STATE_ADMIN` accounts (restricted to admins).
- `POST /api/v1/auth/login` — Issues JWT bearer access token with embedded user role and district jurisdiction.
- `GET /api/v1/auth/me` — Authenticated profile.

### 5.2. Overview & Location Services (`/api/v1/locations` & `/api/v1/overview`)
- `GET /api/v1/locations/states` — List operational states.
- `GET /api/v1/locations/districts` — List districts with boundary metadata and centroids.
- `GET /api/v1/locations/resolve?latitude=...&longitude=...` — Point-in-polygon resolution to district.
- `GET /api/v1/overview?district_id=...` — Unified district situation summary uniting weather/earthquake/fire observations, active alerts, composite risk scores, localized safety guidance, and data source health indicators.

### 5.3. Alert Management Lifecycle (`/api/v1/alerts`)
- `POST /api/v1/alerts` / `POST /api/v1/alerts/draft` — Issue or draft alerts. District officers are strictly barred (HTTP 403) from alerting districts outside their jurisdiction.
- `POST /api/v1/alerts/{id}/issue` — Transition draft to active.
- `POST /api/v1/alerts/{id}/cancel` — Cancel active alert with audit reason.
- `GET /api/v1/alerts/active` — Active public alerts.

### 5.4. Incident Reporting & Verification Workflow (`/api/v1/reports` & `/api/v1/officer`)
- `POST /api/v1/reports` — Citizen incident reporting with non-blocking background intelligence (duplicate detection, scoring).
- `POST /api/v1/reports/{id}/media` — Upload evidence files (JPEG, PNG, MP4, PDF, max 10MB).
- `GET /api/v1/reports/my` — Citizen's own submission history.
- `GET /api/v1/officer/queue?district_id=...` — Officer review queue (strictly scoped to officer's assigned district).
- `POST /api/v1/officer/reports/{id}/review` — Review decision (`verified`, `rejected`, `resolved`).
- `POST /api/v1/officer/reports/{id}/reopen` — Reopening lifecycle with justification notes.

### 5.5. Public Map Publication Security (`/api/v1/map`)
- `GET /api/v1/map/layers?district_id=...` — Unified GeoJSON layers for boundaries, facilities, and verified incidents.
- **Publication Rule**: Unverified and rejected reports are **strictly excluded** from public map feeds to prevent panic and misinformation.

### 5.6. Government Dashboard & Officer Workspace (`/api/v1/officer`)
- `GET /api/v1/officer/metrics` — Live operational counts (`submitted`, `under_review`, `verified`, `rejected`, `resolved`, `unresolved`, `active_alerts`) where $unresolved = submitted + under\_review + verified$.
- `GET /api/v1/officer/reports` — Filterable verification queue scoped strictly to officer jurisdiction.
- `GET /api/v1/officer/reports/{id}/detail` — Comprehensive report inspector uniting media, review timeline, nearby environmental sensors, and scikit-learn TF-IDF duplicate detection clusters.
- `POST /api/v1/officer/reports/{id}/assign` — Assign incident to self and transition status to `under_review`.
- `POST /api/v1/officer/reports/{id}/review` — Formal decision (`verified`, `rejected`, `resolved`) with atomic audit logging.
- `POST /api/v1/officer/reports/{id}/reopen` — Reopens resolved/rejected reports back to `under_review` with incremented counter.
- `GET /api/v1/officer/operational-incidents` — GeoJSON FeatureCollection of all incidents regardless of status for internal officer GIS map.
- `WebSocket /api/v1/officer/ws` — Real-time event broadcasting (`REPORT_CREATED`, `REPORT_ASSIGNED`, `REPORT_REVIEWED`, `REPORT_REOPENED`, `ALERT_CREATED`, `ALERT_ISSUED`, `ALERT_CANCELLED`).

### 5.8. Intelligence & Machine Learning Risk Engine (`/api/v1/intelligence`)
- `GET /api/v1/intelligence/risk/flood` — Deterministic flood risk assessment using IMD rainfall intensity criteria (>20 mm/hr medium, >45 mm/hr high, >70 mm/hr critical) and CWC river stage thresholds.
- `GET /api/v1/intelligence/risk/landslide` — Deterministic landslide susceptibility using GSI slope gradients ($>30^\circ$) and 72-hour antecedent precipitation index triggers ($>150\,mm, >250\,mm$).
- `GET /api/v1/intelligence/risk/district/{id}` — Multi-hazard indicative risk synthesis integrating terrain slope profiles, soil saturation, and ML model concordance.
- `POST /api/v1/intelligence/confidence/evaluate` — Multi-signal explainable confidence scoring (`LOW`, `MEDIUM`, `HIGH`) evaluating coordinate boundary validity, text detail, media attachments, peer corroboration, and sensor consistency.
- `POST /api/v1/intelligence/duplicates/cluster` — Spatio-temporal and TF-IDF semantic duplicate grouping for officer review queues (policy: grouped, never auto-deleted).
- `GET /api/v1/intelligence/ml/benchmark` — scikit-learn model benchmark (`RandomForestClassifier` vs `GradientBoostingClassifier`) on a stratified 80/20 split ($N=600$ benchmark dataset) reporting Accuracy (98.3%), F1-Score, Precision, Recall, 4x4 Confusion Matrix, and Gini Feature Importances.

### 5.9. Audit Logging & Governance (`/api/v1/audit`)
- `GET /api/v1/audit/events` — Immutable administrative event log recording all state mutations with filterable actor and action parameters (accessible to authorized officers and administrators).

---

## 6. Next.js Web Interfaces

The application exposes two dedicated web portals:

### Citizen Web Application
- **Home (`/`)**: State & district selector, active alert cards, live weather & hazard overview, nearby shelter/hospital directory, localized safety instructions.
- **Alert Feed (`/alerts`)**: Live and indicative alerts with severity badges, countdown validity, and hazard filters.
- **Interactive Citizen Map (`/map`)**: Leaflet GIS map with administrative boundaries, critical facilities (hospitals, shelters), and verified public reports only.
- **Report Wizard (`/report`)**: Incident reporting with GPS autofill, interactive map pin drop, and file evidence upload.
- **My Submissions (`/reports/my`)**: Citizen status tracker with timeline progression (`Submitted` $\rightarrow$ `Under Review` $\rightarrow$ `Verified` / `Rejected` $\rightarrow$ `Resolved`).
- **Disaster Preparedness Guide (`/awareness`)**: Multilingual (English / Hindi / Marathi) emergency guides and safety protocols.

### Government Operations Dashboard
- **Command Layout (`/officer`)**: Header persona switcher (`District Officer Mumbai`, `District Officer Pune`, `State Admin MH`, `System Admin`), live WebSocket connectivity badge, and quick stats.
- **Operational Metrics (`/officer`)**: Live database-driven metric cards with drill-down links to verification workflows.
- **Verification Queue (`/officer/queue`)**: Filterable data table with report detail modal, ML duplicate candidates, and one-click actions (`Take Under Review`, `Verify`, `Reject`, `Resolve`, `Reopen`).
- **Targeted Alert Composer (`/officer/alerts/new`)**: Authoritative warning composer with district geo-targeting, simulation/exercise toggle, and citizen alert card preview.
- **Operational GIS Map (`/officer/map`)**: Restricted incident map displaying all pipeline states (unverified, under-review, rejected) with facility capacity inspector.
- **Risk & ML Intelligence Center (`/officer/intelligence`)**: Multi-hazard indicative risk factor synthesis, interactive scikit-learn model benchmark scorecard, 4x4 confusion matrix, duplicate cluster viewer, and explainable credibility sandbox.
- **Audit Viewer (`/officer/audit`)**: Tamper-evident governance viewer with action/actor filters and JSON payload inspection.

---

## 7. Scenario Replay Engine

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

## 8. Running Tests

Run the automated backend test suite:
```bash
docker compose exec -T api pytest -v
```
All 33 tests covering data adapters, geographic resolution, deterministic flood and landslide risk rules, spatio-temporal duplicate detection and clustering, multi-signal explainable confidence scoring, scikit-learn ML baseline training and evaluation, replay lifecycle, 4-role RBAC, overview APIs, alert management, incident submission and review lifecycle, operational metrics calculation, and audit logs are verified and passing.

Run the Phase 5 Intelligence & Risk Engine End-to-End script:
```bash
python test_e2e_phase5.py
```
Validates the complete 7-stage intelligence pipeline including IMD/CWC flood rules, GSI landslide rules, multi-hazard district synthesis, explainable confidence breakdown, duplicate clustering, and scikit-learn model benchmarking.

Run the Phase 4 Government Dashboard End-to-End script:
```bash
python test_e2e_phase4.py
```
Validates the entire 13-step operational lifecycle across live FastAPI, WebSockets, PostGIS, and Redis services.
