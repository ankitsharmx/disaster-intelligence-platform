"""
Earthquake Data Acquisition Module.
Handles:
- Dataset 8: USGS Historical Earthquake Catalogue (2000-present, India bounding box, Mag >= 2.5)
- USGS Recent Earthquake Feed (all_day.geojson)
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone
import requests

from common import download_file, RAW_DIR, compute_sha256

logger = logging.getLogger("earthquake_downloader")

USGS_EVENT_API = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_RECENT_FEED = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"


def download_usgs_recent_feed() -> Dict[str, Any]:
    """Downloads recent global 24-hour earthquake GeoJSON feed."""
    target_dir = RAW_DIR / "earthquake" / "usgs"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "usgs_earthquakes_recent_all_day.geojson"

    logger.info("Downloading USGS recent all_day.geojson feed...")
    success, status, size, sha256_hash = download_file(
        url=USGS_RECENT_FEED,
        target_path=target_path,
        timeout=60,
    )

    return {
        "dataset_id": "usgs_earthquake_recent",
        "name": "USGS Recent Earthquakes (All Day Feed)",
        "filename": target_path.name,
        "path": target_path,
        "url": USGS_RECENT_FEED,
        "success": success,
        "status": status,
        "size": size,
        "sha256": sha256_hash,
        "format": "GeoJSON",
        "is_live_snapshot": True,
    }


def download_usgs_historical_catalogue(
    min_lat: float = 6.0,
    max_lat: float = 38.0,
    min_lon: float = 68.0,
    max_lon: float = 98.0,
    min_magnitude: float = 2.5,
    start_date: str = "2000-01-01",
) -> List[Dict[str, Any]]:
    """
    Downloads historical earthquake events for India bounding box.
    Uses date-bounded intervals (e.g. 2000-2012, 2013-present) to prevent API timeouts or limits.
    """
    target_dir = RAW_DIR / "earthquake" / "usgs"
    target_dir.mkdir(parents=True, exist_ok=True)
    results = []

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    intervals = [
        ("2000-01-01", "2012-12-31", "usgs_earthquakes_india_2000_2012.geojson"),
        ("2013-01-01", now_iso, f"usgs_earthquakes_india_2013_{now_iso[:4]}.geojson"),
    ]

    for start_t, end_t, fname in intervals:
        target_path = target_dir / fname
        params = {
            "format": "geojson",
            "starttime": start_t,
            "endtime": end_t,
            "minmagnitude": str(min_magnitude),
            "minlatitude": str(min_lat),
            "maxlatitude": str(max_lat),
            "minlongitude": str(min_lon),
            "maxlongitude": str(max_lon),
        }

        req = requests.Request("GET", USGS_EVENT_API, params=params)
        full_url = req.prepare().url

        logger.info(f"Downloading USGS historical catalogue [{start_t} to {end_t}] for India bounding box...")
        success, status, size, sha256_hash = download_file(
            url=full_url,
            target_path=target_path,
            timeout=180,
        )

        results.append({
            "dataset_id": "usgs_earthquake_historical",
            "name": f"USGS Historical Earthquake Catalogue ({start_t[:4]}-{end_t[:4]})",
            "filename": fname,
            "path": target_path,
            "url": full_url,
            "success": success,
            "status": status,
            "size": size,
            "sha256": sha256_hash,
            "format": "GeoJSON",
            "is_historical": True,
            "min_magnitude": min_magnitude,
            "bounding_box": [min_lat, min_lon, max_lat, max_lon],
        })

    return results


def run_earthquake_downloads() -> Dict[str, Any]:
    """Orchestrates all earthquake dataset downloads (Dataset 8)."""
    logger.info("Starting Earthquake Datasets Acquisition...")
    res_recent = download_usgs_recent_feed()
    res_hist = download_usgs_historical_catalogue()

    return {
        "recent": res_recent,
        "historical": res_hist,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_earthquake_downloads()
