"""
Multi-Hazard Disaster Intelligence Platform - ML Pipeline
Phase 4: Target Variable & Label Creation (flood_next_72h)

Defines:
- flood_next_72h = 1: A recorded flood event starts in the district within the next 72 hours (t+1, t+2, t+3).
- flood_next_72h = 0: No recorded flood event scheduled to start in this forecast window.
- is_ongoing_flood = 1: District is currently experiencing an ongoing flood (excluded from onset training).
"""

import pandas as pd
import numpy as np
from pathlib import Path

def generate_district_date_labels(district_dates_df, cleaned_events_df, horizon_days=3):
    """
    Given a DataFrame with columns ['district', 'date'],
    computes the target variable 'flood_next_72h' by checking whether any flood event
    in cleaned_events_df starts on (date + 1 day) up to (date + horizon_days).
    """
    print(f"Generating labels for {len(district_dates_df)} district-date observations...")
    
    # Ensure datetime format normalized to midnight
    district_dates_df['date'] = pd.to_datetime(district_dates_df['date']).dt.normalize()
    cleaned_events_df['start_date'] = pd.to_datetime(cleaned_events_df['start_date']).dt.normalize()
    cleaned_events_df['end_date'] = pd.to_datetime(cleaned_events_df['end_date']).dt.normalize()

    # Standardize district strings for join
    district_dates_df['district_clean'] = district_dates_df['district'].astype(str).str.strip().str.lower()
    cleaned_events_df['district_clean'] = cleaned_events_df['district'].astype(str).str.strip().str.lower()

    # Pre-index events by district for rapid lookup
    events_by_dist = {}
    for dist, grp in cleaned_events_df.groupby('district_clean'):
        starts = grp['start_date'].values
        ends = grp['end_date'].values
        events_by_dist[dist] = (starts, ends)

    labels = np.zeros(len(district_dates_df), dtype=int)
    is_ongoing = np.zeros(len(district_dates_df), dtype=int)

    dates = district_dates_df['date'].values
    dists = district_dates_df['district_clean'].values

    one_day_ns = np.timedelta64(1, 'D')
    horizon_ns = np.timedelta64(horizon_days, 'D')

    for i in range(len(district_dates_df)):
        d_name = dists[i]
        d_val = dates[i]

        if d_name not in events_by_dist:
            continue

        starts, ends = events_by_dist[d_name]

        # Check if d_val falls inside ongoing flood [start, end]
        # (Where onset already happened)
        ongoing_mask = (starts <= d_val) & (d_val <= ends)
        if np.any(ongoing_mask):
            is_ongoing[i] = 1

        # Check if any event starts in (d_val, d_val + horizon_days]
        future_mask = (starts > d_val) & (starts <= d_val + horizon_ns)
        if np.any(future_mask):
            labels[i] = 1

    district_dates_df['flood_next_72h'] = labels
    district_dates_df['is_ongoing_flood'] = is_ongoing

    print(f"Label Distribution:")
    print(f"  Positive Onset (flood_next_72h = 1): {labels.sum()} ({labels.mean():.2%})")
    print(f"  Negative (flood_next_72h = 0): {(labels == 0).sum()} ({(labels == 0).mean():.2%})")
    print(f"  Ongoing Floods Flagged: {is_ongoing.sum()} ({is_ongoing.mean():.2%})")

    return district_dates_df
