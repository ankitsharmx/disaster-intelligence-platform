"""
Multi-Hazard Disaster Intelligence Platform - ML Pipeline
Phase 3: Multi-Signal Feature Engineering for Flood Prediction

Constructs:
A. Rainfall Dynamics (1d, 3d, 7d, 14d, 30d accumulations, rolling max, anomaly)
B. Hydrological Sensor Signals (River discharge, stage, 24h delta)
C. Static Geography & Historical Vulnerability (DFSI index, area)
D. Temporal & Monsoon Seasonality (Month, Day of Year, Monsoon flag)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def compute_rolling_rainfall_features(df_daily, rain_col='rain_daily_sum'):
    """
    Computes physical rolling antecedent rainfall accumulations per district.
    R_7d(t) = sum_{i=0}^6 R(t-i)
    """
    print(f"Computing rolling rainfall features across {len(df_daily)} observations...")
    df = df_daily.sort_values(['district', 'date']).copy()

    # 1. Rolling Sums
    grouped = df.groupby('district')[rain_col]
    df['rain_1d'] = df[rain_col]
    df['rain_3d'] = grouped.rolling(window=3, min_periods=1).sum().reset_index(drop=True)
    df['rain_7d'] = grouped.rolling(window=7, min_periods=1).sum().reset_index(drop=True)
    df['rain_14d'] = grouped.rolling(window=14, min_periods=1).sum().reset_index(drop=True)
    df['rain_30d'] = grouped.rolling(window=30, min_periods=1).sum().reset_index(drop=True)

    # 2. Rolling Peaks (Maximum single day rainfall in last 3 and 7 days)
    df['rain_max_3d'] = grouped.rolling(window=3, min_periods=1).max().reset_index(drop=True)
    df['rain_max_7d'] = grouped.rolling(window=7, min_periods=1).max().reset_index(drop=True)

    # 3. Seasonal Anomaly (Deviation from district monthly mean)
    df['month'] = df['date'].dt.month
    monthly_mean = df.groupby(['district', 'month'])['rain_7d'].transform('mean')
    df['rain_anomaly'] = df['rain_7d'] - monthly_mean

    # 4. Temporal Features
    df['day_of_year'] = df['date'].dt.dayofyear
    df['is_monsoon'] = df['month'].isin([6, 7, 8, 9]).astype(int)

    return df

def attach_vulnerability_and_river(df_features, df_river=None, df_dfsi=None):
    """
    Merges river telemetry and static historical vulnerability (DFSI) onto feature matrix.
    """
    df = df_features.copy()

    # Clean district names for merging
    df['district_clean'] = df['district'].astype(str).str.strip().str.lower()

    if df_river is not None and not df_river.empty:
        print("Merging river discharge & level features...")
        df_river['district_clean'] = df_river['district'].astype(str).str.strip().str.lower()
        df_river['date'] = pd.to_datetime(df_river['date']).dt.normalize()

        river_cols = ['district_clean', 'date', 'discharge_mean', 'discharge_max', 
                      'discharge_change_24h', 'rwl_mean', 'rwl_max', 'rwl_change_24h']
        avail_cols = [c for c in river_cols if c in df_river.columns]

        df = pd.merge(df, df_river[avail_cols], on=['district_clean', 'date'], how='left')
        # Impute missing river metrics (e.g., non-sensor districts or quiet days) with 0.0
        for rc in ['discharge_mean', 'discharge_max', 'discharge_change_24h', 'rwl_change_24h']:
            if rc in df.columns:
                df[rc] = df[rc].fillna(0.0)

    if df_dfsi is not None and not df_dfsi.empty:
        print("Merging static historical DFSI index...")
        df_dfsi_clean = df_dfsi.copy()
        # DFSI columns: Unnamed: 0 (District), State_Name, DFSI
        first_col = df_dfsi_clean.columns[0]
        df_dfsi_clean['district_clean'] = df_dfsi_clean[first_col].astype(str).str.strip().str.lower()
        df_dfsi_clean['dfsi_score'] = pd.to_numeric(df_dfsi_clean['DFSI'], errors='coerce')

        df = pd.merge(df, df_dfsi_clean[['district_clean', 'dfsi_score']], on='district_clean', how='left')
        # Fill missing DFSI with median
        median_dfsi = df['dfsi_score'].median() if df['dfsi_score'].notnull().any() else 5.0
        df['dfsi_score'] = df['dfsi_score'].fillna(median_dfsi)

    return df
