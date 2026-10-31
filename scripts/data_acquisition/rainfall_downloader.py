"""
Rainfall and Weather Data Acquisition Module.
Handles:
- Dataset 1: IMD District-wise & State-wise Daily Rainfall (NWDP)
- Dataset 2: IMD Historical Gridded Rainfall (0.25 x 0.25 NetCDF, 1901-2024 from IMD Pune)
- Dataset 3: Open-Meteo Historical Weather (Punjab District Centroids, 2015-2025)
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests

from common import download_file, RAW_DIR, compute_sha256
from nwdp_downloader import download_imd_daily_rainfall

logger = logging.getLogger("rainfall_downloader")

# Precomputed accurate centroids for all 23 administrative districts of Punjab
PUNJAB_DISTRICT_CENTROIDS = [
    {"name": "Amritsar", "lat": 31.6340, "lon": 74.8723},
    {"name": "Barnala", "lat": 30.3819, "lon": 75.5478},
    {"name": "Bathinda", "lat": 30.2110, "lon": 74.9455},
    {"name": "Faridkot", "lat": 30.6769, "lon": 74.7583},
    {"name": "Fatehgarh_Sahib", "lat": 30.6499, "lon": 76.3807},
    {"name": "Fazilka", "lat": 30.4038, "lon": 74.0254},
    {"name": "Firozpur", "lat": 30.9237, "lon": 74.6113},
    {"name": "Gurdaspur", "lat": 32.0419, "lon": 75.4053},
    {"name": "Hoshiarpur", "lat": 31.5273, "lon": 75.9149},
    {"name": "Jalandhar", "lat": 31.3260, "lon": 75.5762},
    {"name": "Kapurthala", "lat": 31.3802, "lon": 75.3819},
    {"name": "Ludhiana", "lat": 30.9010, "lon": 75.8573},
    {"name": "Malerkotla", "lat": 30.5283, "lon": 75.8878},
    {"name": "Mansa", "lat": 29.9880, "lon": 75.3934},
    {"name": "Moga", "lat": 30.8165, "lon": 75.1717},
    {"name": "Muktsar", "lat": 30.4744, "lon": 74.5165},
    {"name": "Pathankot", "lat": 32.2689, "lon": 75.6499},
    {"name": "Patiala", "lat": 30.3398, "lon": 76.3869},
    {"name": "Rupnagar", "lat": 30.9664, "lon": 76.5331},
    {"name": "SAS_Nagar_Mohali", "lat": 30.7046, "lon": 76.7179},
    {"name": "SBS_Nagar_Nawanshahr", "lat": 31.1256, "lon": 76.1187},
    {"name": "Sangrur", "lat": 30.2458, "lon": 75.8421},
    {"name": "Tarn_Taran", "lat": 31.4520, "lon": 74.9255},
]


def download_imd_gridded_netcdf(years: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    """
    Dataset 2: IMD Historical Gridded Rainfall (0.25 x 0.25 degree).
    Downloads annual NetCDF files from IMD Pune using RF25.php POST interface.
    Prioritizes 2020-2024, expanding back as configured.
    """
    target_dir = RAW_DIR / "rainfall" / "imd"
    target_dir.mkdir(parents=True, exist_ok=True)
    results = []

    if years is None:
        # Default priority window: 2020-2024 (approx 125 MB total)
        years = [2024, 2023, 2022, 2021, 2020]

    url = "https://www.imdpune.gov.in/cmpg/Griddata/RF25.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html",
    }

    for yr in years:
        filename = f"ind{yr}_rfp25.nc"
        target_path = target_dir / filename

        logger.info(f"Requesting IMD Gridded Rainfall NetCDF for year {yr}...")
        success, status, size, sha256_hash = download_file(
            url=url,
            target_path=target_path,
            post_data={"RF25": str(yr)},
            headers=headers,
            timeout=180,
        )

        results.append({
            "dataset_id": "imd_gridded_rainfall_netcdf",
            "name": f"IMD Gridded Daily Rainfall 0.25deg ({yr})",
            "year": yr,
            "filename": filename,
            "path": target_path,
            "url": url,
            "success": success,
            "status": status,
            "size": size,
            "sha256": sha256_hash,
            "format": "NetCDF",
        })
        time.sleep(1)  # Respectful pause

    return results


def download_open_meteo_historical_weather(
    districts: Optional[List[Dict[str, Any]]] = None,
    start_date: str = "2015-01-01",
    end_date: str = "2024-12-31",
) -> List[Dict[str, Any]]:
    """
    Dataset 3: Open-Meteo Historical Weather (ERA5 / ERA5-Land reanalysis).
    Downloads historical hourly weather for Punjab district centroids.
    Variables: temperature_2m, relative_humidity_2m, precipitation, rain,
               wind_speed_10m, wind_direction_10m, surface_pressure.
    """
    target_dir = RAW_DIR / "rainfall" / "open_meteo"
    target_dir.mkdir(parents=True, exist_ok=True)
    results = []

    if districts is None:
        districts = PUNJAB_DISTRICT_CENTROIDS

    api_url = "https://archive-api.open-meteo.com/v1/archive"

    for dist in districts:
        dist_name = dist["name"]
        filename = f"open_meteo_weather_{dist_name}_{start_date[:4]}_{end_date[:4]}.csv"
        target_path = target_dir / filename

        params = {
            "latitude": dist["lat"],
            "longitude": dist["lon"],
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m,wind_direction_10m,surface_pressure",
            "format": "csv",
        }

        # Build full URL with query string
        req = requests.Request("GET", api_url, params=params)
        prepared_url = req.prepare().url

        logger.info(f"Downloading Open-Meteo historical weather for Punjab district: {dist_name}...")
        success, status, size, sha256_hash = download_file(
            url=prepared_url,
            target_path=target_path,
            timeout=120,
        )

        results.append({
            "dataset_id": "open_meteo_historical_weather",
            "district": dist_name,
            "name": f"Open-Meteo Weather {dist_name} ({start_date[:4]}-{end_date[:4]})",
            "filename": filename,
            "path": target_path,
            "url": prepared_url,
            "success": success,
            "status": status,
            "size": size,
            "sha256": sha256_hash,
            "format": "CSV",
            "start_date": start_date,
            "end_date": end_date,
        })
        time.sleep(1)  # Respect API rate limits

    return results


def run_rainfall_downloads() -> Dict[str, Any]:
    """Orchestrates all rainfall and weather downloads (Datasets 1, 2, 3)."""
    logger.info("Starting Rainfall & Weather Datasets Acquisition...")
    res1 = download_imd_daily_rainfall()
    res2 = download_imd_gridded_netcdf()
    res3 = download_open_meteo_historical_weather()

    return {
        "imd_daily": res1,
        "imd_gridded": res2,
        "open_meteo": res3,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_rainfall_downloads()
