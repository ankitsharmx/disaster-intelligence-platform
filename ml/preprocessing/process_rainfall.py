"""
Multi-Hazard Disaster Intelligence Platform - ML Pipeline
Phase 2.2: Process Gridded & Station Rainfall Datasets

1. Maps IMD 0.25° grid coordinates to administrative district polygons using spatial indexing.
2. Extracts daily district-level rainfall metrics:
   - rain_mean: Average rainfall over district (mm)
   - rain_max: Maximum grid-cell rainfall (mm)
   - rain_p90: 90th percentile rainfall (mm)
   - heavy_rain_area_pct: % of district grid cells > 50 mm/day
3. Also aggregates Open-Meteo hourly weather into daily district observations for Punjab (2015-2024).
"""

import sys
import numpy as np
import pandas as pd
import xarray as xr
import geopandas as gpd
from shapely.geometry import Point
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def build_grid_district_mapping(district_gdf, lats, lons):
    """
    Precomputes spatial mapping from IMD grid points (lat, lon) to district polygons.
    Runs once and allows instant vectorized raster zonal aggregation.
    """
    print(f"Building spatial index for {len(lats)}x{len(lons)} grid across {len(district_gdf)} districts...")
    grid_points = []
    lat_indices = []
    lon_indices = []

    for i, lat in enumerate(lats):
        for j, lon in enumerate(lons):
            grid_points.append(Point(lon, lat))
            lat_indices.append(i)
            lon_indices.append(j)

    gdf_grid = gpd.GeoDataFrame(
        {'lat_idx': lat_indices, 'lon_idx': lon_indices, 'lat': [p.y for p in grid_points], 'lon': [p.x for p in grid_points]},
        geometry=grid_points,
        crs="EPSG:4326"
    )

    # Ensure district_gdf is EPSG:4326
    if district_gdf.crs != "EPSG:4326":
        district_gdf = district_gdf.to_crs("EPSG:4326")

    # Spatial join: match grid points to containing district
    joined = gpd.sjoin(gdf_grid, district_gdf[['dtcode', 'district', 'state_name', 'geometry']], how='inner', predicate='within')
    print(f"Mapped {len(joined)} grid points within India administrative districts.")
    return joined

def process_imd_gridded_rainfall():
    project_root = Path(__file__).resolve().parents[2]
    raw_dir = project_root / "data" / "raw"
    processed_dir = project_root / "data" / "processed" / "rainfall"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_parquet = processed_dir / "imd_district_daily_rainfall_2020_2024.parquet"

    boundary_file = raw_dir / "geography" / "district_boundaries" / "district_nwic_geojson" / "district_nwic.GeoJSON"
    nc_files = sorted(list((raw_dir / "rainfall" / "imd").glob("ind*.nc")))

    if not nc_files or not boundary_file.exists():
        print("[!] Required NetCDF or boundary GeoJSON not found.")
        return

    # Load boundaries
    print(f"Loading district boundaries from {boundary_file.name}...")
    dist_gdf = gpd.read_file(boundary_file)

    # Sample NC for grid coords
    ds_sample = xr.open_dataset(nc_files[0])
    lats = ds_sample['LATITUDE'].values
    lons = ds_sample['LONGITUDE'].values

    # Precompute spatial mapping
    mapping = build_grid_district_mapping(dist_gdf, lats, lons)
    point_indices = mapping[['lat_idx', 'lon_idx', 'dtcode', 'district', 'state_name']].copy()

    all_district_daily = []

    for nc_file in nc_files:
        print(f"\nProcessing NetCDF: {nc_file.name}...")
        ds = xr.open_dataset(nc_file)
        # RF shape: (TIME, LAT, LON)
        rf_array = ds['RAINFALL'].values
        # Handle time coords
        times = pd.to_datetime(ds['TIME'].values)
        
        # Replace negative values with 0
        rf_array = np.where(rf_array < 0, 0.0, rf_array)
        rf_array = np.nan_to_num(rf_array, nan=0.0)

        lat_idx = point_indices['lat_idx'].values
        lon_idx = point_indices['lon_idx'].values
        dtcodes = point_indices['dtcode'].values
        districts = point_indices['district'].values
        states = point_indices['state_name'].values

        # Extract values for mapped grid points across all days: shape (T, P)
        mapped_rf = rf_array[:, lat_idx, lon_idx]

        for t_idx, current_date in enumerate(times):
            day_values = mapped_rf[t_idx, :]
            df_day = pd.DataFrame({
                'dtcode': dtcodes,
                'district': districts,
                'state': states,
                'rainfall': day_values
            })

            # Vectorized aggregation per district
            grouped = df_day.groupby(['dtcode', 'district', 'state'])['rainfall'].agg(
                rain_mean='mean',
                rain_max='max',
                rain_p90=lambda x: np.percentile(x, 90) if len(x) > 0 else 0.0,
                heavy_rain_area_pct=lambda x: (x >= 50.0).mean() * 100.0
            ).reset_index()

            grouped['date'] = current_date
            all_district_daily.append(grouped)

    df_result = pd.concat(all_district_daily, ignore_index=True)
    df_result['date'] = pd.to_datetime(df_result['date']).dt.normalize()
    print(f"\nAggregated {len(df_result)} district-day observations across {df_result['district'].nunique()} districts.")
    df_result.to_parquet(out_parquet, index=False)
    print(f"Saved IMD district daily rainfall to: {out_parquet}")
    return df_result

def process_open_meteo_punjab():
    """
    Processes the 23 Punjab hourly Open-Meteo CSVs into clean daily aggregated time-series.
    """
    project_root = Path(__file__).resolve().parents[2]
    om_dir = project_root / "data" / "raw" / "rainfall" / "open_meteo"
    processed_dir = project_root / "data" / "processed" / "rainfall"
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_parquet = processed_dir / "punjab_open_meteo_daily_2015_2024.parquet"

    csv_files = sorted(list(om_dir.glob("open_meteo_weather_*.csv")))
    print(f"\nProcessing {len(csv_files)} Punjab Open-Meteo district archives (2015-2024)...")

    daily_records = []
    for f in csv_files:
        district_name = f.stem.replace("open_meteo_weather_", "").replace("_2015_2024", "").replace("_", " ")
        df = pd.read_csv(f, skiprows=3)
        # Normalize column names by substring matching
        col_map = {}
        for c in df.columns:
            cl = c.lower()
            if 'precip' in cl: col_map[c] = 'precipitation'
            elif 'temp' in cl: col_map[c] = 'temperature_2m'
            elif 'humid' in cl: col_map[c] = 'relative_humidity_2m'
            elif 'wind_speed' in cl: col_map[c] = 'wind_speed_10m'
        df = df.rename(columns=col_map)

        df['time'] = pd.to_datetime(df['time'], errors='coerce')
        df = df[df['time'].notnull()].copy()
        df['date'] = df['time'].dt.normalize()

        daily = df.groupby('date').agg(
            rain_daily_sum=('precipitation', 'sum'),
            rain_max_1h=('precipitation', 'max'),
            temp_mean=('temperature_2m', 'mean'),
            temp_max=('temperature_2m', 'max'),
            humidity_mean=('relative_humidity_2m', 'mean'),
            wind_max=('wind_speed_10m', 'max')
        ).reset_index()

        daily['district'] = district_name
        daily['state'] = 'Punjab'
        daily_records.append(daily)

    df_om = pd.concat(daily_records, ignore_index=True)
    print(f"Generated {len(df_om)} daily district observations for Punjab across {df_om['district'].nunique()} districts.")
    df_om.to_parquet(out_parquet, index=False)
    print(f"Saved Open-Meteo Punjab daily weather to: {out_parquet}")
    return df_om

if __name__ == "__main__":
    process_open_meteo_punjab()
    process_imd_gridded_rainfall()
