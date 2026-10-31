"""
Multi-Hazard Disaster Intelligence Platform
Phase 1: Generate Visualizations & Statistical Summaries for Data Audit
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import xarray as xr
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
raw_dir = project_root / "data" / "raw"
fig_dir = project_root / "ml" / "reports" / "figures"
fig_dir.mkdir(parents=True, exist_ok=True)

# Set aesthetics
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['axes.edgecolor'] = '#cccccc'
plt.rcParams['axes.linewidth'] = 0.8

print("[1] Loading India Flood Inventory...")
df_inv = pd.read_csv(raw_dir / "flood" / "india_flood_inventory" / "India_Flood_Inventory_v3.csv")
df_inv['start_dt'] = pd.to_datetime(df_inv['Start Date'], errors='coerce')
df_inv['year'] = df_inv['start_dt'].dt.year
df_inv['month'] = df_inv['start_dt'].dt.month
df_inv['duration'] = pd.to_numeric(df_inv['Duration(Days)'], errors='coerce')

# --- Fig 1: Flood events by year ---
plt.figure(figsize=(12, 5))
yearly = df_inv['year'].dropna().astype(int).value_counts().sort_index()
sns.barplot(x=yearly.index, y=yearly.values, color='#1f77b4')
plt.title("Historical Flood Events by Year (India Flood Inventory 1967–2023)", fontsize=13, weight='bold')
plt.xlabel("Year", fontsize=11)
plt.ylabel("Number of Documented Events", fontsize=11)
plt.xticks(rotation=70, fontsize=8)
plt.tight_layout()
plt.savefig(fig_dir / "flood_events_by_year.png", dpi=300)
plt.close()
print("Saved flood_events_by_year.png")

# --- Fig 2: Top 15 States by Flood Events ---
plt.figure(figsize=(10, 6))
# Handle multi-state events by splitting
states_series = df_inv['State'].dropna().str.split(',').explode().str.strip()
top_states = states_series.value_counts().head(15)
sns.barplot(y=top_states.index, x=top_states.values, palette='Blues_r')
plt.title("Top 15 States by Recorded Flood Events (1967–2023)", fontsize=13, weight='bold')
plt.xlabel("Number of Events", fontsize=11)
plt.ylabel("State", fontsize=11)
plt.tight_layout()
plt.savefig(fig_dir / "flood_events_by_state.png", dpi=300)
plt.close()
print("Saved flood_events_by_state.png")

# --- Fig 3: Monthly Event Distribution (Seasonality) ---
plt.figure(figsize=(9, 4.5))
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
monthly = df_inv['month'].dropna().astype(int).value_counts().reindex(range(1, 13), fill_value=0)
colors = ['#aec7e8' if m not in [6, 7, 8, 9] else '#d62728' for m in range(1, 13)]
sns.barplot(x=month_names, y=monthly.values, palette=colors)
plt.title("Seasonality: Monthly Flood Event Frequency (Monsoon Surge in Jul-Aug)", fontsize=13, weight='bold')
plt.xlabel("Month", fontsize=11)
plt.ylabel("Number of Flood Onset Events", fontsize=11)
plt.tight_layout()
plt.savefig(fig_dir / "flood_events_by_month.png", dpi=300)
plt.close()
print("Saved flood_events_by_month.png")

# --- Fig 4: Missing Value Heatmap ---
plt.figure(figsize=(12, 6))
key_cols = ['UEI', 'Start Date', 'End Date', 'Duration(Days)', 'Main Cause', 'Districts', 'State', 
            'Severity', 'Area Affected', 'Human fatality', 'Human injured', 'Human Displaced', 'District_LGD_Codes']
missing = df_inv[key_cols].isnull().astype(int)
sns.heatmap(missing.T, cbar=False, cmap=['#2ca02c', '#d62728'], yticklabels=key_cols)
plt.title("Missing Value Matrix for Flood Inventory (Green: Present, Red: Missing)", fontsize=13, weight='bold')
plt.xlabel("Event Index", fontsize=11)
plt.tight_layout()
plt.savefig(fig_dir / "missing_values_heatmap.png", dpi=300)
plt.close()
print("Saved missing_values_heatmap.png")

# --- Fig 5: Flood Event Duration Distribution ---
plt.figure(figsize=(9, 4.5))
dur = df_inv['duration'].dropna()
dur_clipped = dur[dur <= 30] # Clip for visualization
sns.histplot(dur_clipped, bins=30, kde=True, color='#2ca02c')
plt.axvline(dur.median(), color='red', linestyle='--', label=f'Median Duration: {dur.median():.0f} days')
plt.axvline(dur.mean(), color='orange', linestyle=':', label=f'Mean Duration: {dur.mean():.1f} days')
plt.title("Flood Event Duration Distribution (Days)", fontsize=13, weight='bold')
plt.xlabel("Duration in Days (clipped at 30 days)", fontsize=11)
plt.ylabel("Frequency", fontsize=11)
plt.legend()
plt.tight_layout()
plt.savefig(fig_dir / "flood_event_duration.png", dpi=300)
plt.close()
print("Saved flood_event_duration.png")

# --- Fig 6: Rainfall Distribution (IMD Gridded 2024 Sample) ---
nc_path = raw_dir / "rainfall" / "imd" / "ind2024_rfp25.nc"
if nc_path.exists():
    print("[2] Processing sample IMD NetCDF for rainfall distribution...")
    ds = xr.open_dataset(nc_path)
    # Take monsoon peak day (e.g., Aug 10, 2024)
    rf = ds['RAINFALL'].values
    valid_rf = rf[~np.isnan(rf) & (rf > 0.1)].flatten()
    
    plt.figure(figsize=(9, 4.5))
    sns.histplot(valid_rf, bins=50, log_scale=(True, False), color='#17becf')
    plt.title("IMD Daily Gridded Rainfall Intensity Distribution (2024 Non-Zero Cells, Log Scale)", fontsize=13, weight='bold')
    plt.xlabel("Daily Rainfall (mm, log scale)", fontsize=11)
    plt.ylabel("Grid Cell Count", fontsize=11)
    plt.tight_layout()
    plt.savefig(fig_dir / "rainfall_distribution_log.png", dpi=300)
    plt.close()
    print("Saved rainfall_distribution_log.png")

print("\nAll figures generated successfully.")
