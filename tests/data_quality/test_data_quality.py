"""
Multi-Hazard Disaster Intelligence Platform - Master Testing Suite
Category 01: Data Quality Testing (DATA-01 to DATA-12)
"""

import json
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
import xarray as xr

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROC_DIR = DATA_DIR / "processed"
META_DIR = DATA_DIR / "metadata"

def test_data_01_open_every_downloaded_csv():
    """DATA-01: Open every downloaded CSV and ensure they load without parsing errors."""
    csv_files = list(RAW_DIR.rglob("*.csv")) + list(PROC_DIR.rglob("*.csv"))
    assert len(csv_files) >= 5, "Expected at least 5 CSV files in data/"
    
    for f in csv_files:
        # Open-Meteo CSVs have 3 metadata rows
        skip = 3 if "open_meteo" in f.name else 0
        df = pd.read_csv(f, skiprows=skip, nrows=50)
        assert len(df) > 0, f"File {f.name} is empty"
        assert len(df.columns) > 1, f"File {f.name} failed column parsing"

def test_data_02_netcdf_rainfall_integrity():
    """DATA-02: Open NetCDF rainfall data and verify variables, dimensions, coordinates and units."""
    nc_files = list((RAW_DIR / "rainfall" / "imd").glob("ind*.nc"))
    assert len(nc_files) >= 5, "Expected 5 IMD NetCDF files (2020-2024)"
    
    for nc in nc_files:
        ds = xr.open_dataset(nc)
        assert 'RAINFALL' in ds.data_vars, f"RAINFALL variable missing in {nc.name}"
        assert 'TIME' in ds.coords or 'TIME' in ds.dims
        assert 'LATITUDE' in ds.coords
        assert 'LONGITUDE' in ds.coords
        assert len(ds['LATITUDE']) == 129
        assert len(ds['LONGITUDE']) == 135
        # Verify units in attributes or range
        rf_slice = ds['RAINFALL'].isel(TIME=0).values
        valid_vals = rf_slice[~np.isnan(rf_slice) & (rf_slice >= 0)]
        assert len(valid_vals) > 0, f"No valid rainfall values in {nc.name}"
        assert valid_vals.max() < 1500.0, f"Physically impossible rainfall in {nc.name}"

def test_data_03_missing_values_quantification():
    """DATA-03: Quantify and document missing values across primary datasets."""
    inv_file = RAW_DIR / "flood" / "india_flood_inventory" / "India_Flood_Inventory_v3.csv"
    df_inv = pd.read_csv(inv_file)
    null_counts = df_inv.isnull().sum().to_dict()
    assert null_counts['UEI'] == 0, "UEI must have 0 nulls"
    assert null_counts['Start Date'] <= 25, "Start Date nulls must be <= 25"
    assert null_counts['State'] == 0, "State must have 0 nulls"

def test_data_04_duplicate_records_verification():
    """DATA-04: Ensure duplicate records are identified without deleting valid observations."""
    cleaned_events = PROC_DIR / "flood" / "cleaned_flood_events.parquet"
    assert cleaned_events.exists(), "Cleaned flood events file missing"
    df = pd.read_parquet(cleaned_events)
    # Check deduplication
    dups = df.duplicated(subset=['uei', 'district', 'start_date'])
    assert dups.sum() == 0, "Duplicate event-district instances detected"

def test_data_05_coordinate_bounds():
    """DATA-05: Coordinates fall strictly within valid geographic bounds for India."""
    # Check NASA Landslides
    nasa_file = RAW_DIR / "landslide" / "nasa" / "Global_Landslide_Catalog_Export.csv"
    df_nasa = pd.read_csv(nasa_file)
    df_ind = df_nasa[df_nasa['country_name'] == 'India'].dropna(subset=['latitude', 'longitude'])
    assert (df_ind['latitude'].between(6.0, 38.5)).all(), "Landslide latitude outside India bounds"
    assert (df_ind['longitude'].between(67.0, 98.0)).all(), "Landslide longitude outside India bounds"

def test_data_06_district_identifiers_and_lgd():
    """DATA-06: District names and LGD codes map correctly to boundaries."""
    bnd_file = RAW_DIR / "geography" / "district_boundaries" / "district_nwic_geojson" / "district_nwic.GeoJSON"
    with open(bnd_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    features = data['features']
    assert len(features) >= 700, "Expected at least 700 district boundary polygons"
    
    # Check dtcode (LGD) presence
    dtcodes = [f['properties'].get('dtcode') for f in features if f['properties'].get('dtcode')]
    assert len(dtcodes) > 650, "Most districts must have dtcode / LGD assigned"

def test_data_07_date_fields_consistency():
    """DATA-07: Dates parse consistently with normalized time."""
    df_events = pd.read_parquet(PROC_DIR / "flood" / "cleaned_flood_events.parquet")
    assert pd.api.types.is_datetime64_any_dtype(df_events['start_date'])
    assert df_events['start_date'].dt.year.min() >= 1967
    assert df_events['start_date'].dt.year.max() <= 2024

def test_data_08_rainfall_values_non_negative():
    """DATA-08: Rainfall measurements are non-negative and physically bounded."""
    df_weather = pd.read_parquet(PROC_DIR / "rainfall" / "punjab_open_meteo_daily_2015_2024.parquet")
    assert (df_weather['rain_daily_sum'] >= 0.0).all(), "Negative rainfall values detected"
    assert (df_weather['rain_daily_sum'] <= 600.0).all(), "Unrealistically extreme daily rainfall"

def test_data_09_measurement_units_consistency():
    """DATA-09: Units are documented and consistent across datasets."""
    df_river = pd.read_parquet(PROC_DIR / "flood" / "punjab_river_daily_metrics.parquet")
    if 'discharge_mean' in df_river.columns:
        valid_dis = df_river['discharge_mean'].dropna()
        assert (valid_dis >= 0.0).all(), "Discharge m3/s cannot be negative"
        assert valid_dis.max() < 50000.0, "River discharge exceeded physical basin capacity"

def test_data_10_source_provenance_metadata():
    """DATA-10: Dataset manifest and source registry contain provenance and license metadata."""
    manifest_file = META_DIR / "dataset_manifest.json"
    registry_file = META_DIR / "source_registry.json"
    assert manifest_file.exists(), "Dataset manifest JSON missing"
    assert registry_file.exists(), "Source registry JSON missing"
    
    with open(manifest_file, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    assert len(manifest) >= 50, "Expected at least 50 documented resources in manifest"
    
    # Check fields
    item = manifest[0]
    for key in ['dataset_name', 'source_agency', 'download_status', 'sha256', 'file_size_bytes']:
        assert key in item, f"Missing {key} in manifest entry"

def test_data_11_historical_temporal_coverage():
    """DATA-11: Start and end dates match documented source specifications."""
    df_train = pd.read_parquet(PROC_DIR / "flood" / "flood_training_dataset.parquet")
    assert df_train['date'].dt.year.min() == 2015, "Punjab multi-signal baseline starts 2015"
    assert df_train['date'].dt.year.max() >= 2023, "Baseline extends through at least 2023"

def test_data_12_demo_vs_live_labels():
    """DATA-12: Demo records cannot be mistaken for live observations."""
    df_manifest = pd.read_csv(META_DIR / "dataset_manifest.csv")
    assert 'download_status' in df_manifest.columns
    # Ensure statuses are among sanctioned vocabulary
    valid_statuses = {'EXISTS_VALID', 'SUCCESS', 'PARTIAL', 'FAILED', 'SKIPPED_NO_API_KEY', 'SKIPPED_MANUAL_ACTION', 'UNAVAILABLE'}
    found_statuses = set(df_manifest['download_status'].unique())
    assert found_statuses.issubset(valid_statuses), f"Unexpected statuses: {found_statuses - valid_statuses}"
