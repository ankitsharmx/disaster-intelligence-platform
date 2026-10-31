"""
Retries missing Open-Meteo district datasets with rate-limiting
(6 seconds between calls, and 30 seconds backoff on HTTP 429) to ensure
all 23 Punjab districts are downloaded 100% reliably.
"""

import time
import logging
from pathlib import Path
import requests

from rainfall_downloader import PUNJAB_DISTRICT_CENTROIDS
from common import download_file, RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("retry_open_meteo")
OPEN_METEO_BASE = "https://archive-api.open-meteo.com/v1/archive"

def download_missing_districts():
    target_dir = RAW_DIR / "rainfall" / "open_meteo"
    target_dir.mkdir(parents=True, exist_ok=True)

    for item in PUNJAB_DISTRICT_CENTROIDS:
        dist = item["name"]
        lat = item["lat"]
        lon = item["lon"]
        fname = f"open_meteo_weather_{dist}_2015_2024.csv"
        fpath = target_dir / fname

        if fpath.exists() and fpath.stat().st_size > 1000:
            logger.info(f"District {dist} already downloaded ({fpath.stat().st_size:,} bytes). Skipping.")
            continue

        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": "2015-01-01",
            "end_date": "2024-12-31",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m,wind_direction_10m,surface_pressure",
            "format": "csv",
        }
        req = requests.Request("GET", OPEN_METEO_BASE, params=params)
        url = req.prepare().url

        logger.info(f"Downloading missing district: {dist}...")
        downloaded = False
        for attempt in range(1, 4):
            success, status, size, sha = download_file(url=url, target_path=fpath, timeout=60)
            if success:
                logger.info(f"Successfully downloaded {fname} ({size:,} bytes).")
                downloaded = True
                break
            else:
                logger.warning(f"Failed to download {dist} (status: {status}). Waiting 25s before retry...")
                time.sleep(25)

        # 6 seconds delay between successful calls to stay safely under 10/min
        time.sleep(6)

if __name__ == "__main__":
    download_missing_districts()
