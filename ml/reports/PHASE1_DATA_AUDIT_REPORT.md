# Multi-Hazard Disaster Intelligence Platform
## Phase 1: Dataset Audit & Feasibility Exploration Report (Flood Risk Model)

**Date of Audit:** October 30, 2026  
**Auditor:** Senior Data & Geospatial ML Engineer  
**Target Model:** Indicative Flood-Event Probability (Next 72 Hours)

---

## 1. Executive Summary

Before writing training code for our predictive flood risk engine, we conducted a rigorous audit of all downloaded public datasets. We examined schema integrity, date coverage, geographic linkages (LGD codes), null distributions, and spatial/temporal overlaps between event labels and predictor observations.

### Key Audit Findings:
1. **Target Event Data is Plentiful and Spatially Specific:**
   - The **IIT Delhi India Flood Inventory (`India_Flood_Inventory_v3.csv`)** contains **6,876 documented flood events** spanning 1967 to 2023.
   - **99.1% (6,817 out of 6,876) of events contain explicit district identifiers**, with 6,572 containing Local Government Directory (LGD) district codes.
   - Expanding multi-district events produces **24,628 unique district-event onset instances** covering **882 district names** and **685 LGD codes**.
2. **Temporal Overlap with High-Resolution Predictors:**
   - **2020–2023 National Window:** 826 national flood events overlap directly with our high-resolution **IMD 0.25° gridded daily rainfall NetCDF-4 archives (2020–2024)**.
   - **2015–2023 Regional Focus (Punjab):** Open-Meteo hourly weather (2015–2024 across all 23 Punjab districts) + Punjab Water Resources River Discharge (624,300 telemetry records) + River Water Level telemetry provide a continuous multi-signal sensor baseline for hydrological flood modeling.
3. **Data Usability & Leakage Safeguard:**
   - `DFSI.csv`, `District_FloodedArea.csv`, and `District_FloodImpact.csv` are static historical vulnerability summaries (744 districts). As mandated by the architecture guidelines, **they will not be fed as predictor features** into the event prediction model, eliminating target leakage.

---

## 2. Dataset-by-Dataset Audit Results

### 2.1. India Flood Inventory (`India_Flood_Inventory_v3.csv`)
- **Total Records:** 6,876 rows × 23 columns
- **Date Range:** 1967-01-08 to 2023-12-09
- **Columns & Completeness:**
  - `UEI` (Unique Event Identifier): 0 nulls (100% complete, format `UEI-IMD-FL-YYYY-XXXX`)
  - `Start Date`: 20 nulls (99.7% complete)
  - `End Date`: 24 nulls (99.7% complete)
  - `Duration(Days)`: Median 6.0 days, Mean 9.2 days, Max 184 days
  - `Districts`: 59 nulls (99.1% coverage)
  - `District_LGD_Codes`: 304 nulls (95.6% coverage)
  - `Severity`, `Area Affected`, `Human fatality`: Sparse (~40% populated; outcome metrics, not predictors)
- **Multi-District Breakdown:**
  - Single-district events: 4,474 events
  - Multi-district events: 2,402 events (affecting up to 35 districts per regional monsoon surge)
  - Exploded district-event records: **24,628 records**

### 2.2. Historical District Vulnerability References (`DFSI.csv`, Area, Impact)
- **DFSI (District Flood Severity Index):** 744 districts. Top severity: Patna (19.30), Murshidabad (18.91), Muzaffarpur (18.23).
- **Flooded Area & Impact:** 732 districts recording historical inundated percentages and casualty records.
- **Architectural Role:** Contextual metadata & dashboard comparison only; isolated from feature matrix $X$.

### 2.3. IMD 0.25° Daily Gridded Rainfall (`ind2020_rfp25.nc` to `ind2024_rfp25.nc`)
- **Format:** NetCDF-4, grid resolution 0.25° × 0.25° (~27 km).
- **Dimensions:** `TIME: 365/366`, `LATITUDE: 129` (6.5°N to 38.5°N), `LONGITUDE: 135` (66.5°E to 100.0°E).
- **Variable:** `RAINFALL` (float32, mm/day). Missing value: `NaN` / `-999.0`.
- **Integrity:** Zero corrupted slices. Readily sliced and zonal-aggregated across district polygons.

### 2.4. Open-Meteo Hourly Weather (23 Punjab Districts, 2015–2024)
- **Records:** 87,672 hourly rows per district (~2,016,000 hourly observations total).
- **Variables:** Hourly precipitation (mm), temperature (2m), relative humidity (2m), wind speed (10m).
- **Completeness:** 100% complete with no missing timestamps. Can be aggregated to daily sums, max 1h precipitation, and rolling 3d/7d/14d antecedent moisture.

### 2.5. Punjab River Water Level & Discharge Telemetry
- **Discharge (`river_discharge_tele_hr_punjab_sw_pb_1970_2025.csv`):** 624,300 rows. Covers major rivers (Sutlej, Beas, Ravi) with telemetry hourly discharge ($m^3/\text{sec}$).
- **River Water Level (`rwl_tel_hr_punjab_sw_999_2021_2025.csv`):** 46,840 rows with sensor stage in meters.
- **District Mapping:** Each station explicitly records `District LGD Code` (e.g., Firozpur, Ludhiana, Rupnagar, Kapurthala), enabling direct catchment-to-district joining.

### 2.6. Administrative Boundaries (`district_nwic.GeoJSON`)
- **Features:** 733 administrative district polygons.
- **Key Attributes:** `dtcode` (LGD District Code), `district`, `stcode`, `state_name`.
- **CRS:** EPSG:7755 (India National Coordinate System), reprojectable to EPSG:4326 for GIS raster intersection.

---

## 3. Exploratory Data Analysis & Visualizations

The following diagnostic charts have been generated and saved to `ml/reports/figures/`:

1. **`flood_events_by_year.png`**: Documents the surge in recorded events from 1967 to 2023, with peak documentation density occurring between 2000 and 2023.
2. **`flood_events_by_state.png`**: Top affected states include Assam, Bihar, Uttar Pradesh, West Bengal, Maharashtra, Odisha, and Punjab.
3. **`flood_events_by_month.png`**: Stark seasonal monsoon spike during July (31.4%) and August (36.2%), confirming that temporal features (`month`, `is_monsoon`) will carry heavy predictive weight.
4. **`missing_values_heatmap.png`**: Validates that core event features (`Start Date`, `Districts`, `District_LGD_Codes`) are dense, while post-disaster damage variables are sparse.
5. **`flood_event_duration.png`**: Reveals that 75% of flood events have an active duration of 3 to 14 days, with a sharp mode at 7 days.
6. **`rainfall_distribution_log.png`**: Demonstrates the heavy right-tail of monsoon precipitation intensity ($>50\text{ mm/day}$ to $>200\text{ mm/day}$).

---

## 4. Key Limitations & Methodological Safeguards

### 4.1. Unrecorded Days vs. True Absence (Negative Class Definition)
- **Challenge:** The flood inventory is an *event catalogue*, not a daily census. A date with no entry does not strictly prove zero inundation.
- **Safeguard:**
  - Define $y=1$ strictly as **documented flood onset within the next 72 hours**.
  - Sample negative days ($y=0$) with priority given to confirmed low-rainfall / low-river periods, while labeling the evaluation metric as indicative onset probability rather than absolute flood absence.
  - Transparently document this in platform API disclaimers.

### 4.2. Onset vs. Ongoing Flooding
- **Challenge:** Labeling every day of a 14-day flood as a positive prediction target creates label leakage and inflates recall.
- **Safeguard:** We align target labels strictly to the **72-hour window preceding the event Start Date**. Days inside an active ongoing flood are excluded from training the *onset* classifier.

### 4.3. Spatial Splitting & Autocorrelation
- **Challenge:** A single meteorological event impacts adjacent districts simultaneously. Random cross-validation will cause data leakage.
- **Safeguard:**
  - **Temporal Split:** Train on historical years (e.g. 2015–2021), validate on 2022, and test on 2023 unseen future monsoon seasons.
  - **Spatial Holdout:** Evaluate cross-district generalization by withholding 20% of districts entirely from training.

---

## 5. Phase 1 Conclusion & Sign-Off

The downloaded data is **fully sufficient, rich, and verified** for training an enterprise-grade indicative flood risk model.

### Next Step: Phase 2 (Data Cleaning & Geographic Aggregation)
We are ready to proceed with:
1. Standardizing district names and LGD codes using `clean_flood_inventory.py`.
2. Zonal grid aggregation of daily IMD NetCDF rainfall onto district boundary polygons (`process_rainfall.py`).
3. Station-to-district mapping of Punjab river discharge and water levels (`process_river_data.py`).
