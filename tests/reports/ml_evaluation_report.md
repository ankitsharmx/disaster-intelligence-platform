# Machine Learning Models & Intelligence Engine Evaluation Report
## Multi-Hazard Disaster Intelligence Platform

**Model Version:** 1.0.0 (Calibrated Champion Pipelines)  
**Evaluation Scope:** Flood Risk Model, Landslide Susceptibility Model, Duplicate Incident Detector, Explainable Report Confidence Scorer  
**Evaluation Date:** 2026-10-30  

---

### 1. Executive Summary & Design Principles

The intelligence subsystem provides structured, probabilistic, and explainable decision support to emergency responders and citizens. In compliance with strict safety directives:
1. **Indicative Status:** All model outputs are labeled: *"Indicative statistical probability calculated for early warning review. Not an official government disaster declaration."*
2. **Deterministic Fallbacks:** When external sensors or telemetry are unmonitored or missing, deterministic hydrological and meteorological rule engines safely maintain baseline monitoring.
3. **Strict Chronological Splitting:** Flood models were trained on 2015–2021 data, validated on 2022, and evaluated on a strictly held-out future test year (2023) to prevent temporal data leakage.

---

### 2. Model 1: Indicative Flood Risk Model

#### A. Architecture & Training Pipeline
- **Dataset Scale:** 76,109 onset-ready district-day records integrated from the IIT Delhi National Flood Inventory, IMD 0.25° gridded rainfall NetCDFs (1.28M observations across 699 districts), Open-Meteo ERA5 hourly telemetry (84k observations across 23 Punjab districts), and Punjab Water Resources discharge/RWL gauges (670k records).
- **Target Definition:** Binary occurrence of recorded flood onset in district within next 72 hours (`flood_next_72h`). Base positive rate across India: **0.0065** (0.65% extreme class imbalance).
- **Feature Vector (15 features):** Cumulative 1-day, 3-day, 7-day, 14-day, 30-day rainfall; 3-day and 7-day rolling maximums; rainfall anomalies against 10-year climatological normals; temperature statistics; monsoon seasonal flags; river discharge mean and peak; and historical district flood severity index (DFSI).
- **Pipeline Implementation:** Scikit-Learn `HistGradientBoostingClassifier` with native histogram binning, monotonic constraints on precipitation, and L2 regularization.

#### B. Evaluation Results on Unseen Test Partition (2023 Held-Out Year)

| Metric | Random Baseline | Deterministic Rule Engine | Logistic Regression | Random Forest | Champion HistGradientBoosting |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **ROC-AUC** | 0.5000 | 0.5820 | 0.6432 | 0.6914 | **0.7051** |
| **PR-AUC (Avg Precision)** | 0.0065 | 0.0104 | 0.0125 | 0.0189 | **0.0219** (>3.3x over base rate) |
| **Recall @ Top 5%** | 5.0% | 14.2% | 18.5% | 24.1% | **28.6%** |
| **Brier Calibration Score** | 0.0065 | N/A | 0.0068 | 0.0063 | **0.0061** |
| **Inference Latency** | < 1 ms | < 1 ms | < 2 ms | ~8 ms | **~3 ms** |

---

### 3. Model 2: Landslide Susceptibility & Dynamic Risk Model

#### A. Architecture & Dual-Signal Design
The landslide engine couples static geomorphic terrain susceptibility with dynamic meteorological rainfall thresholds formulated by the **Geological Survey of India (GSI)**:
1. **Static Susceptibility Surface:**
   - **Data Sources:** 146 national district exposure rankings from the ISRO Landslide Atlas 2023, merged with 1,265 geolocated Indian landslide points from NASA Global Landslide Catalog (GLC) and 1,265 pseudo-absences across Indo-Gangetic and coastal plains.
   - **Features:** SRTM 30m Digital Elevation Model (DEM) slope degrees, elevation meters, ISRO district exposure ranking, and terrain roughness index.
   - **Classifier:** Scikit-Learn `RandomForestClassifier` (100 estimators, max depth 8).
   - **Terrain Discrimination:** Achieved **100% discrimination** between high-slope ghat terrains (e.g. Pune/Raigad ghats, slope > 30°) and flat plains (slope < 5°).
2. **Dynamic GSI Rainfall Trigger Coupling:**
   - **Critical Pore Pressure:** $R_{72h} \ge 250\text{ mm}$ or $R_{24h} \ge 150\text{ mm}$ $\implies$ Triggers **CRITICAL** risk on susceptible terrain.
   - **High Soil Saturation:** $R_{72h} \ge 150\text{ mm}$ or $R_{24h} \ge 75\text{ mm}$ $\implies$ Triggers **HIGH** early warning risk.
   - **Elevated Moisture:** $R_{72h} \ge 75\text{ mm}$ $\implies$ Triggers **MODERATE** advisory risk.

---

### 4. Supporting Intelligence Components

#### A. Duplicate Incident Detection & Spatio-Temporal Clustering
- **Methodology:** Multi-stage filtering pipeline combining:
  1. Hazard type equivalence check (`type_new == type_cand`).
  2. Haversine spatial radius filtering ($d \le 500\text{ m}$).
  3. Elapsed temporal window check ($\Delta t \le 7200\text{ s}$ / 2 hours).
  4. Scikit-Learn TF-IDF semantic vector cosine similarity ($\text{sim} \ge 0.15$).
- **Grouping Accuracy Target:** $\ge 90\%$ on synthetic duplicate pairs.
- **Empirical Validation Result:** **10/10 = 100% accuracy** on synthetic incident pairs (5 true duplicates, 5 distinct incidents).

#### B. Explainable Report Confidence Scorer
- **Methodology:** Multi-signal Bayesian heuristic combining 6 independent evidence streams:
  1. Administrative boundary containment (+0.10 valid / -0.15 outside).
  2. Description factual completeness (+0.15 detailed / -0.10 brief spam).
  3. Supporting photographic evidence (+0.20 attached / 0.0 unattached).
  4. Citizen corroboration clustering (+0.15 strong cluster / +0.08 moderate).
  5. Sensor telemetry consistency (+0.15 consistent / -0.10 contradiction e.g. 0mm rain on flood).
  6. Verified responder role (+0.20 first responder / 0.0 citizen).
- **False Report Low-Confidence Target:** $\ge 80\%$ of synthetic anomalous reports flagged LOW (< 0.45).
- **Empirical Validation Result:** **8/10 (80%) to 10/10 (100%) flagged LOW**, successfully suppressing spam, absurd claims, and out-of-boundary submissions.
