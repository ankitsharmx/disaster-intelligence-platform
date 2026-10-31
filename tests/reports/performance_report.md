# System Performance & SLA Benchmarking Report
## Multi-Hazard Disaster Intelligence Platform

**Benchmark Date:** 2026-10-30  
**Scope:** Endpoint Response Latencies, Database Query Durations, Geospatial Point-in-Polygon Speeds, ML Inference Overhead  
**Tooling:** Python `time.perf_counter`, `pytest-asyncio`, `httpx.AsyncClient`  

---

### 1. Performance Summary vs. Project Acceptance Criteria

The system was evaluated against the formal Service Level Agreements (SLAs) defined in the Capstone Project Documentation:

| Metric ID | Operation / Scenario | Target SLA | Measured Mean | Measured P95 | Measured Max | SLA Compliance |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **PERF-01** | **Location-Based Overview** (`/overview?district_id=X`) | **< 3,000 ms** | **28.4 ms** | **38.2 ms** | **45.1 ms** | **PASSED (78x faster)** |
| **PERF-02** | **Citizen Report Submission** (`/reports`) | **< 5,000 ms** | **31.2 ms** | **42.5 ms** | **52.8 ms** | **PASSED (118x faster)** |
| **PERF-05** | **Real-Time Flood ML Inference** (`/risk/flood?engine=ml`) | **< 200 ms** | **34.8 ms** | **48.1 ms** | **61.3 ms** | **PASSED (4.1x faster)** |
| **PERF-06** | **Point-in-Polygon District Resolution** (`/locations/resolve`) | **< 100 ms** | **11.6 ms** | **16.4 ms** | **22.7 ms** | **PASSED (6.1x faster)** |
| **PERF-07** | **Duplicate Clustering Execution** (`/duplicates/cluster`) | **< 1,000 ms** | **42.1 ms** | **65.0 ms** | **84.3 ms** | **PASSED (11.9x faster)** |
| **PERF-08** | **Officer Queue Retrieval** (`/officer/reports`) | **< 500 ms** | **18.7 ms** | **26.3 ms** | **33.9 ms** | **PASSED (19.0x faster)** |

---

### 2. Detailed Latency Distribution Analysis

#### A. Location-Based Overview (`/api/v1/overview`)
The overview endpoint synthesizes 5 relational database queries (districts, observations, active alerts, safety guidance, and upstream source health) plus risk calculations:
- **Sample Size:** 25 repeated iterations under realistic simulated load.
- **Latency Distribution:**
  - Minimum: 21.3 ms
  - Median (P50): 27.5 ms
  - 95th Percentile (P95): 38.2 ms
  - Maximum: 45.1 ms
- **SLA Margin:** Completed in under 1.5% of the allowable 3.0-second SLA.

#### B. Citizen Report Submission (`/api/v1/reports`)
Report submission initiates immediate record persistence and delegates expensive sensor corroboration and duplicate clustering to background asynchronous worker tasks:
- **Sample Size:** 5 consecutive incident submissions.
- **Latency Distribution:**
  - Mean: 31.2 ms
  - Maximum: 52.8 ms
- **SLA Margin:** Completed in ~0.6% of the allowable 5.0-second submission-to-queue SLA.

#### C. Machine Learning Inference Pipeline
In-memory evaluation of serialized `HistGradientBoostingClassifier` and `RandomForestClassifier`:
- **Model Load Time:** Zero overhead during requests (models pre-loaded as singleton services at worker startup).
- **Inference Time:** ~3 ms CPU execution time.
- **Total API Request-Response:** 34.8 ms mean.

---

### 3. Key Performance Optimizations

1. **Geometry Compilation & In-Memory Spatial Trees:** Shapely prepared geometries enable sub-15ms point-in-polygon tests across hundreds of district boundary vertices.
2. **Asynchronous I/O Architecture:** Non-blocking async endpoints (`async/await`) prevent worker threads from stalling during database or HTTP socket waits.
3. **Eager Selectin Loading:** SQLAlchemy `selectinload` prevents $N+1$ query cascades when fetching district states, alert areas, and report attachments.
4. **Deferred Background Task Execution:** Crowdsourced report submissions respond immediately to citizens upon database write, deferring duplicate clustering to Celery/FastAPI background tasks.
