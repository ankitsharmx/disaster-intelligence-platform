"""
Multi-Hazard Disaster Intelligence Platform - ML Pipeline
Phase 2.3: Process Punjab River Discharge & Stage Telemetry

Aggregates high-frequency sensor readings (hourly) into daily district hydrological metrics:
- Mean and peak river discharge (m3/s)
- Discharge rate of change (24h)
- Mean and peak river water stage (meters)
- River level rate of change (24h)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def process_punjab_river_telemetry():
    project_root = Path(__file__).resolve().parents[2]
    raw_dir = project_root / "data" / "raw" / "flood" / "punjab_water_department"
    processed_dir = project_root / "data" / "processed" / "flood"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_parquet = processed_dir / "punjab_river_daily_metrics.parquet"

    dis_file = raw_dir / "river_discharge_tele_hr_punjab_sw_pb_1970_2025.csv"
    rwl_file = raw_dir / "rwl_tel_hr_punjab_sw_999_2021_2025.csv"

    print("=" * 70)
    print("PHASE 2.3: PROCESSING PUNJAB RIVER HYDROLOGICAL DATA")
    print("=" * 70)

    # 1. Process Discharge
    print(f"\nLoading river discharge: {dis_file.name}...")
    df_dis = pd.read_csv(dis_file, usecols=[
        'District LGD Code', 'District', 'Data Acquisition Time', 
        'Telemetry Hourly River Water Discharge (m3/sec)'
    ])
    df_dis = df_dis.rename(columns={
        'District LGD Code': 'lgd_code',
        'District': 'district',
        'Data Acquisition Time': 'acq_time',
        'Telemetry Hourly River Water Discharge (m3/sec)': 'discharge_m3s'
    })
    
    # Parse dates
    df_dis['datetime'] = pd.to_datetime(df_dis['acq_time'], dayfirst=True, errors='coerce')
    df_dis = df_dis[df_dis['datetime'].notnull()].copy()
    df_dis['date'] = df_dis['datetime'].dt.normalize()
    df_dis['discharge_m3s'] = pd.to_numeric(df_dis['discharge_m3s'], errors='coerce').fillna(0.0)

    # Standardize district names
    df_dis['district'] = df_dis['district'].astype(str).str.strip().str.title()

    # Daily aggregation per district
    dis_daily = df_dis.groupby(['district', 'date']).agg(
        discharge_mean=('discharge_m3s', 'mean'),
        discharge_max=('discharge_m3s', 'max'),
        discharge_std=('discharge_m3s', 'std')
    ).reset_index()
    dis_daily['discharge_std'] = dis_daily['discharge_std'].fillna(0.0)

    # Calculate 24h change by sorting and shifting
    dis_daily = dis_daily.sort_values(['district', 'date'])
    dis_daily['discharge_change_24h'] = dis_daily.groupby('district')['discharge_mean'].diff().fillna(0.0)
    print(f"Aggregated {len(dis_daily)} daily discharge records across {dis_daily['district'].nunique()} districts.")

    # 2. Process River Water Level (RWL)
    print(f"\nLoading river water level: {rwl_file.name}...")
    df_rwl = pd.read_csv(rwl_file, usecols=[
        'District LGD Code', 'District', 'Data Acquisition Time',
        'River Water Level Telemetry Hourly (meter)'
    ])
    df_rwl = df_rwl.rename(columns={
        'District LGD Code': 'lgd_code',
        'District': 'district',
        'Data Acquisition Time': 'acq_time',
        'River Water Level Telemetry Hourly (meter)': 'rwl_m'
    })
    df_rwl['datetime'] = pd.to_datetime(df_rwl['acq_time'], dayfirst=True, errors='coerce')
    df_rwl = df_rwl[df_rwl['datetime'].notnull()].copy()
    df_rwl['date'] = df_rwl['datetime'].dt.normalize()
    df_rwl['rwl_m'] = pd.to_numeric(df_rwl['rwl_m'], errors='coerce')
    df_rwl = df_rwl.dropna(subset=['rwl_m'])

    df_rwl['district'] = df_rwl['district'].astype(str).str.strip().str.title()

    rwl_daily = df_rwl.groupby(['district', 'date']).agg(
        rwl_mean=('rwl_m', 'mean'),
        rwl_max=('rwl_m', 'max')
    ).reset_index()

    rwl_daily = rwl_daily.sort_values(['district', 'date'])
    rwl_daily['rwl_change_24h'] = rwl_daily.groupby('district')['rwl_mean'].diff().fillna(0.0)
    print(f"Aggregated {len(rwl_daily)} daily water level records across {rwl_daily['district'].nunique()} districts.")

    # 3. Outer Merge Hydrological Features
    merged = pd.merge(dis_daily, rwl_daily, on=['district', 'date'], how='outer')
    merged['state'] = 'Punjab'
    merged = merged.sort_values(['district', 'date'])

    print(f"\nCombined daily hydrological records: {len(merged)}")
    merged.to_parquet(out_parquet, index=False)
    print(f"Saved to: {out_parquet}")
    return merged

if __name__ == "__main__":
    process_punjab_river_telemetry()
