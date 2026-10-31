"""
Multi-Hazard Disaster Intelligence Platform
Phase 1: Deep-Dive Audit of Flood Inventory & Spatial Overlap
"""

import pandas as pd
import numpy as np
import geopandas as gpd
from pathlib import Path
import json

project_root = Path(__file__).resolve().parents[2]
raw_dir = project_root / "data" / "raw"
reports_dir = project_root / "ml" / "reports"

df_inv = pd.read_csv(raw_dir / "flood" / "india_flood_inventory" / "India_Flood_Inventory_v3.csv")

print(f"Total raw inventory rows: {len(df_inv)}")
print("Null counts in key fields:")
print(f"  UEI: {df_inv['UEI'].isnull().sum()}")
print(f"  Start Date: {df_inv['Start Date'].isnull().sum()}")
print(f"  Districts: {df_inv['Districts'].isnull().sum()}")
print(f"  District_LGD_Codes: {df_inv['District_LGD_Codes'].isnull().sum()}")
print(f"  State: {df_inv['State'].isnull().sum()}")

# Parse Start Date
df_inv['start_dt'] = pd.to_datetime(df_inv['Start Date'], errors='coerce')
df_inv['year'] = df_inv['start_dt'].dt.year

# Filter rows with district info
has_dist = df_inv['Districts'].notnull() | df_inv['District_LGD_Codes'].notnull()
print(f"\nEvents with district information: {has_dist.sum()} / {len(df_inv)} ({has_dist.mean():.1%})")
print(f"Events with only state information (no district): {(~has_dist).sum()}")

# Analyze year distribution of district-level events
df_dist_events = df_inv[has_dist].copy()
year_counts = df_dist_events['year'].value_counts().sort_index()
print("\nDistrict-level event count by year range:")
print(f"  1967-1999: {year_counts.loc[year_counts.index < 2000].sum()}")
print(f"  2000-2014: {year_counts.loc[(year_counts.index >= 2000) & (year_counts.index < 2015)].sum()}")
print(f"  2015-2019: {year_counts.loc[(year_counts.index >= 2015) & (year_counts.index < 2020)].sum()}")
print(f"  2020-2023: {year_counts.loc[(year_counts.index >= 2020) & (year_counts.index <= 2023)].sum()}")

# Explode multi-district rows
exploded_records = []
for idx, row in df_dist_events.iterrows():
    dists = str(row['Districts']).split(',') if pd.notnull(row['Districts']) else []
    lgds = str(row['District_LGD_Codes']).split(',') if pd.notnull(row['District_LGD_Codes']) else []
    
    # Strip whitespace
    dists = [d.strip() for d in dists if d.strip() and d.strip().lower() != 'nan']
    lgds = [l.strip() for l in lgds if l.strip() and l.strip().lower() != 'nan']
    
    max_len = max(len(dists), len(lgds), 1)
    for i in range(max_len):
        d_name = dists[i] if i < len(dists) else (dists[0] if dists else None)
        l_code = lgds[i] if i < len(lgds) else (lgds[0] if lgds else None)
        exploded_records.append({
            "uei": row['UEI'],
            "start_date": row['start_dt'],
            "year": row['year'],
            "duration_days": row['Duration(Days)'],
            "state": row['State'],
            "district": d_name,
            "lgd_code": l_code,
            "severity": row['Severity']
        })

df_exploded = pd.DataFrame(exploded_records)
print(f"\nExploded district-event records: {len(df_exploded)}")
print(f"Unique districts named: {df_exploded['district'].nunique()}")
print(f"Unique LGD codes: {df_exploded['lgd_code'].nunique()}")

# Punjab check
pb_events = df_exploded[df_exploded['state'].str.contains('punjab', case=False, na=False)]
print(f"\nPunjab specific district-event records: {len(pb_events)}")
if not pb_events.empty:
    print(f"Punjab years covered: {sorted(pb_events['year'].dropna().unique().tolist())}")
    print(f"Punjab districts in events: {pb_events['district'].value_counts().to_dict()}")

# Inspect District Boundaries
shp_path = raw_dir / "geography" / "district_boundaries" / "district_nwic_shp" / "district_nwic.shp"
geojson_path = raw_dir / "geography" / "district_boundaries" / "district_nwic_geojson" / "district_nwic.GeoJSON"
geoboundaries_path = raw_dir / "geography" / "district_boundaries" / "geoBoundaries_IND_ADM2.geojson"

boundary_file = None
if geojson_path.exists():
    boundary_file = geojson_path
elif geoboundaries_path.exists():
    boundary_file = geoboundaries_path

if boundary_file:
    print(f"\nInspecting district boundary file: {boundary_file.name}")
    gdf = gpd.read_file(boundary_file)
    print(f"Boundary features count: {len(gdf)}")
    print(f"Boundary columns: {list(gdf.columns)}")
    print(f"CRS: {gdf.crs}")
    print("Sample boundary row:")
    print(gdf.drop(columns='geometry').head(2).to_dict(orient='records'))

print("\nAudit Deep Dive completed successfully.")
