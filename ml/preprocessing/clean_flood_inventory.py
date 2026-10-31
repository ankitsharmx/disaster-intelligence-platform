"""
Multi-Hazard Disaster Intelligence Platform - ML Pipeline
Phase 2.1: Clean and Normalize India Flood Inventory

Transforms raw India_Flood_Inventory_v3.csv into standardized,
exploded district-event records with validated LGD codes and timestamps.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json

def clean_flood_inventory():
    project_root = Path(__file__).resolve().parents[2]
    raw_file = project_root / "data" / "raw" / "flood" / "india_flood_inventory" / "India_Flood_Inventory_v3.csv"
    processed_dir = project_root / "data" / "processed" / "flood"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_parquet = processed_dir / "cleaned_flood_events.parquet"
    out_csv = processed_dir / "cleaned_flood_events.csv"

    print(f"Reading raw inventory: {raw_file}")
    df = pd.read_csv(raw_file)

    # 1. Standardize column names
    col_map = {
        'UEI': 'uei',
        'Start Date': 'start_date_raw',
        'End Date': 'end_date_raw',
        'Duration(Days)': 'duration_days_raw',
        'Main Cause': 'cause',
        'Districts': 'districts_raw',
        'State': 'state_raw',
        'Severity': 'severity_raw',
        'District_LGD_Codes': 'lgd_codes_raw',
        'State_Codes': 'state_codes_raw'
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # 2. Parse dates with dayfirst=True for Indian DD-MM-YYYY format
    df['start_date'] = pd.to_datetime(df['start_date_raw'], dayfirst=True, errors='coerce')
    df['end_date'] = pd.to_datetime(df['end_date_raw'], dayfirst=True, errors='coerce')

    # Remove rows without valid start_date
    initial_len = len(df)
    df = df[df['start_date'].notnull()].copy()
    print(f"Filtered {initial_len - len(df)} events with invalid start_date. Remaining: {len(df)}")

    # 3. Numeric duration
    df['duration_days'] = pd.to_numeric(df['duration_days_raw'], errors='coerce')
    # If duration missing but end_date present, calculate
    mask_missing_dur = df['duration_days'].isnull() & df['end_date'].notnull()
    df.loc[mask_missing_dur, 'duration_days'] = (
        (df.loc[mask_missing_dur, 'end_date'] - df.loc[mask_missing_dur, 'start_date']).dt.total_seconds() / 86400.0
    ).clip(lower=1.0)
    df['duration_days'] = df['duration_days'].fillna(1.0)

    # 4. Explode multi-district entries
    cleaned_rows = []
    skipped_no_district = 0

    for _, row in df.iterrows():
        dists_str = str(row['districts_raw']) if pd.notnull(row.get('districts_raw')) else ''
        lgds_str = str(row['lgd_codes_raw']) if pd.notnull(row.get('lgd_codes_raw')) else ''

        dists = [d.strip() for d in dists_str.split(',') if d.strip() and d.strip().lower() != 'nan']
        lgds = [l.strip() for l in lgds_str.split(',') if l.strip() and l.strip().lower() != 'nan']

        if not dists and not lgds:
            skipped_no_district += 1
            continue

        count = max(len(dists), len(lgds), 1)
        for i in range(count):
            d_name = dists[i] if i < len(dists) else (dists[0] if dists else None)
            l_code = lgds[i] if i < len(lgds) else (lgds[0] if lgds else None)

            # Clean LGD code (digits only)
            l_code_clean = None
            if l_code:
                digits = "".join([c for c in l_code if c.isdigit()])
                if digits:
                    l_code_clean = int(digits)

            cleaned_rows.append({
                'uei': row['uei'],
                'start_date': row['start_date'],
                'end_date': row['end_date'],
                'duration_days': float(row['duration_days']),
                'year': int(row['start_date'].year),
                'month': int(row['start_date'].month),
                'day': int(row['start_date'].day),
                'state': str(row.get('state_raw', '')).strip(),
                'district': str(d_name).strip() if d_name else None,
                'lgd_code': l_code_clean,
                'severity': str(row.get('severity_raw', '')).strip() if pd.notnull(row.get('severity_raw')) else 'UNKNOWN',
                'cause': str(row.get('cause', '')).strip() if pd.notnull(row.get('cause')) else 'flood'
            })

    df_clean = pd.DataFrame(cleaned_rows)
    print(f"Skipped {skipped_no_district} state-only events lacking district identifiers.")
    print(f"Generated {len(df_clean)} standardized district-event onset records.")

    # Deduplicate exact duplicate event-district-date tuples
    df_clean = df_clean.drop_duplicates(subset=['uei', 'district', 'start_date'])
    print(f"After deduplication: {len(df_clean)} records across {df_clean['district'].nunique()} districts.")

    # Save output
    df_clean.to_parquet(out_parquet, index=False)
    df_clean.to_csv(out_csv, index=False)
    print(f"Saved cleaned flood events to:\n  - {out_parquet}\n  - {out_csv}")
    return df_clean

if __name__ == "__main__":
    clean_flood_inventory()
