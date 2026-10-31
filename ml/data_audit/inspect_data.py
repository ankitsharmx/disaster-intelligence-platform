"""
Multi-Hazard Disaster Intelligence Platform - ML Pipeline
Phase 1: Dataset Auditing and Exploration for Flood Risk Modeling

Inspects:
1. India_Flood_Inventory_v3.csv (Historical flood event inventory)
2. DFSI.csv (District Flood Severity Index)
3. District_FloodedArea.csv (Historical inundated area)
4. District_FloodImpact.csv (Historical casualties & damage metrics)
5. IMD daily rainfall (District-wise CSV & Gridded NetCDF-4)
6. Punjab Water Resources Department (RWL & Discharge)
7. District Boundaries (NWIC GeoJSON / Shapefile)
"""

import sys
import os
import json
from pathlib import Path
import pandas as pd
import numpy as np

def run_audit():
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    raw_dir = data_dir / "raw"
    reports_dir = project_root / "ml" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    audit_summary = {}

    print("=" * 80)
    print("PHASE 1: DATA AUDIT & EXPLORATION FOR FLOOD RISK PREDICTION")
    print("=" * 80)

    # 1. India Flood Inventory
    inv_file = raw_dir / "flood" / "india_flood_inventory" / "India_Flood_Inventory_v3.csv"
    if inv_file.exists():
        print(f"\n[1] Inspecting India Flood Inventory: {inv_file.name}")
        df_inv = pd.read_csv(inv_file)
        audit_summary["flood_inventory"] = {
            "total_rows": len(df_inv),
            "columns": list(df_inv.columns),
            "null_counts": df_inv.isnull().sum().to_dict(),
            "dtypes": {col: str(dtype) for col, dtype in df_inv.dtypes.items()}
        }
        print(f"Shape: {df_inv.shape}")
        print(f"Columns: {list(df_inv.columns)}")
        print(f"Sample Head:\n{df_inv.head(2).to_dict(orient='records')}")

        # Check date range
        start_col = [c for c in df_inv.columns if "start" in c.lower()][0]
        end_col = [c for c in df_inv.columns if "end" in c.lower()][0]
        df_inv['parsed_start'] = pd.to_datetime(df_inv[start_col], errors='coerce')
        df_inv['parsed_end'] = pd.to_datetime(df_inv[end_col], errors='coerce')
        
        valid_dates = df_inv['parsed_start'].dropna()
        audit_summary["flood_inventory"]["min_date"] = str(valid_dates.min()) if not valid_dates.empty else None
        audit_summary["flood_inventory"]["max_date"] = str(valid_dates.max()) if not valid_dates.empty else None
        print(f"Date Range: {audit_summary['flood_inventory']['min_date']} to {audit_summary['flood_inventory']['max_date']}")

        # Geographic distribution (States / Districts)
        state_col = [c for c in df_inv.columns if "state" in c.lower()][0]
        dist_col = [c for c in df_inv.columns if "dist" in c.lower()][0]
        unique_states = df_inv[state_col].dropna().unique().tolist()
        audit_summary["flood_inventory"]["unique_states_count"] = len(unique_states)
        audit_summary["flood_inventory"]["unique_states"] = sorted(unique_states)
        print(f"Unique States: {len(unique_states)}")

        # Multi-district entries analysis
        multi_district_count = df_inv[dist_col].dropna().apply(lambda x: len(str(x).split(',')) if ',' in str(x) else 1)
        audit_summary["flood_inventory"]["events_with_multiple_districts"] = int((multi_district_count > 1).sum())
        audit_summary["flood_inventory"]["single_district_events"] = int((multi_district_count == 1).sum())
        print(f"Events affecting multiple districts: {(multi_district_count > 1).sum()} / {len(df_inv)}")
    else:
        print(f"[!] File not found: {inv_file}")

    # 2. DFSI (District Flood Severity Index)
    dfsi_file = raw_dir / "flood" / "india_flood_inventory" / "DFSI.csv"
    if dfsi_file.exists():
        print(f"\n[2] Inspecting DFSI: {dfsi_file.name}")
        df_dfsi = pd.read_csv(dfsi_file)
        audit_summary["dfsi"] = {
            "total_rows": len(df_dfsi),
            "columns": list(df_dfsi.columns),
            "null_counts": df_dfsi.isnull().sum().to_dict()
        }
        print(f"Shape: {df_dfsi.shape}, Columns: {list(df_dfsi.columns)}")
        print(f"Sample:\n{df_dfsi.head(2).to_dict(orient='records')}")

    # 3. District Flooded Area & Impact
    area_file = raw_dir / "flood" / "india_flood_inventory" / "District_FloodedArea.csv"
    impact_file = raw_dir / "flood" / "india_flood_inventory" / "District_FloodImpact.csv"
    if area_file.exists():
        df_area = pd.read_csv(area_file)
        audit_summary["flooded_area"] = {"rows": len(df_area), "columns": list(df_area.columns)}
        print(f"\n[3] District Flooded Area: {df_area.shape}")
    if impact_file.exists():
        df_impact = pd.read_csv(impact_file)
        audit_summary["flood_impact"] = {"rows": len(df_impact), "columns": list(df_impact.columns)}
        print(f"[4] District Flood Impact: {df_impact.shape}")

    # 4. IMD District-wise Daily Rainfall
    imd_dist_file = raw_dir / "rainfall" / "imd" / "rainfall_districtwise_daily_imd.csv"
    if imd_dist_file.exists():
        print(f"\n[5] Inspecting IMD District-wise Daily Rainfall: {imd_dist_file.name}")
        df_imd = pd.read_csv(imd_dist_file)
        audit_summary["imd_districtwise"] = {
            "total_rows": len(df_imd),
            "columns": list(df_imd.columns),
            "null_counts": df_imd.isnull().sum().to_dict(),
            "dtypes": {col: str(dtype) for col, dtype in df_imd.dtypes.items()}
        }
        print(f"Shape: {df_imd.shape}, Columns: {list(df_imd.columns)}")
        date_candidates = [c for c in df_imd.columns if "date" in c.lower() or "time" in c.lower()]
        if date_candidates:
            df_imd['parsed_date'] = pd.to_datetime(df_imd[date_candidates[0]], errors='coerce')
            audit_summary["imd_districtwise"]["min_date"] = str(df_imd['parsed_date'].dropna().min())
            audit_summary["imd_districtwise"]["max_date"] = str(df_imd['parsed_date'].dropna().max())
            print(f"Date Coverage: {audit_summary['imd_districtwise']['min_date']} to {audit_summary['imd_districtwise']['max_date']}")

    # 5. IMD Gridded NetCDF files
    nc_dir = raw_dir / "rainfall" / "imd"
    nc_files = sorted(list(nc_dir.glob("*.nc")))
    audit_summary["imd_gridded_nc"] = {"files": [f.name for f in nc_files]}
    print(f"\n[6] Found {len(nc_files)} IMD NetCDF files: {[f.name for f in nc_files]}")
    if nc_files:
        try:
            import xarray as xr
            sample_nc = nc_files[-1] # inspect the latest 2024
            ds = xr.open_dataset(sample_nc)
            audit_summary["imd_gridded_nc"]["sample_dims"] = {str(k): int(v) for k, v in ds.dims.items()}
            audit_summary["imd_gridded_nc"]["data_vars"] = list(ds.data_vars.keys())
            audit_summary["imd_gridded_nc"]["coords"] = list(ds.coords.keys())
            print(f"NetCDF ({sample_nc.name}) Dims: {ds.dims}")
            print(f"Data Variables: {list(ds.data_vars.keys())}")
            print(f"Coords: {list(ds.coords.keys())}")
        except Exception as e:
            print(f"xarray inspection error: {e}")

    # 6. Punjab Water Resources (River Level & Discharge)
    pb_dir = raw_dir / "flood" / "punjab_water_department"
    pb_files = sorted(list(pb_dir.glob("*.csv")))
    print(f"\n[7] Punjab Water Dept Files: {[f.name for f in pb_files]}")
    pb_summary = {}
    for pf in pb_files:
        try:
            df_p = pd.read_csv(pf, nrows=5)
            # count total rows
            row_count = sum(1 for _ in open(pf, 'r', encoding='utf-8', errors='ignore')) - 1
            pb_summary[pf.name] = {
                "rows": row_count,
                "columns": list(df_p.columns)
            }
            print(f"  - {pf.name}: {row_count} rows, cols: {list(df_p.columns)}")
        except Exception as e:
            pb_summary[pf.name] = {"error": str(e)}
    audit_summary["punjab_water_dept"] = pb_summary

    # Save summary json
    out_json = reports_dir / "phase1_data_audit.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=2, default=str)
    print(f"\nSaved audit summary to: {out_json}")

if __name__ == "__main__":
    run_audit()
