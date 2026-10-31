"""
Forest Fire Data Acquisition Module.
Handles:
- Dataset 12: Forest Survey of India (FSI) Historical Fire Data (Archival Search & CSV Export)
- Dataset 13: NASA FIRMS (Checks NASA_FIRMS_MAP_KEY, records SKIPPED_NO_API_KEY if absent)
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
from bs4 import BeautifulSoup

from common import download_file, RAW_DIR, compute_sha256

logger = logging.getLogger("fire_downloader")

FSI_SEARCH_URL = "https://fsiforestfire.gov.in/ArchivalData/Search"
FSI_DOWNLOAD_URL = "https://fsiforestfire.gov.in/ArchivalData/DownloadCsv"


def download_fsi_historical_fires(
    state: str = "PUNJAB",
    from_date: str = "2004-12-01",
    to_date: str = "2025-06-30",
    sensor: str = "",
) -> Dict[str, Any]:
    """
    Dataset 12: Forest Survey of India (FSI) Historical Fire Points.
    Navigates the official archival search portal, retrieves verification tokens,
    submits query parameters for state and date range, and downloads the resulting CSV.
    """
    target_dir = RAW_DIR / "forest_fire" / "fsi"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_filename = f"fsi_forest_fire_{state.lower()}_{from_date[:4]}_{to_date[:4]}.csv"
    target_path = target_dir / target_filename

    logger.info(f"Initiating FSI Archival Fire Search for {state} ({from_date} to {to_date})...")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    })

    try:
        # Step 1: GET search page to obtain CSRF verification token
        r_get = session.get(FSI_SEARCH_URL, verify=False, timeout=30)
        soup_get = BeautifulSoup(r_get.text, "html.parser")
        token_elem = soup_get.find("input", {"name": "__RequestVerificationToken"})
        token = token_elem.get("value") if token_elem else ""

        # Step 2: POST search parameters
        search_payload = {
            "__RequestVerificationToken": token,
            "FromDate": from_date,
            "ToDate": to_date,
            "SelectedSensor": sensor,
            "SelectedState": state,
        }
        r_post = session.post(FSI_SEARCH_URL, data=search_payload, verify=False, timeout=60)
        soup_post = BeautifulSoup(r_post.text, "html.parser")

        # Step 3: Extract inputs for /ArchivalData/DownloadCsv
        csv_form = soup_post.find("form", {"action": "/ArchivalData/DownloadCsv"})
        if not csv_form:
            logger.error("DownloadCsv form not found in FSI search response.")
            return {
                "dataset_id": "fsi_historical_forest_fire",
                "name": f"FSI Historical Forest Fire ({state})",
                "filename": target_filename,
                "path": None,
                "url": FSI_DOWNLOAD_URL,
                "success": False,
                "status": "FAILED",
                "size": 0,
                "sha256": None,
                "format": "CSV",
            }

        download_payload = {}
        for inp in csv_form.find_all("input"):
            download_payload[inp.get("name")] = inp.get("value")

        # Step 4: Stream download CSV response
        r_csv = session.post(FSI_DOWNLOAD_URL, data=download_payload, verify=False, stream=True, timeout=90)
        if r_csv.status_code == 200:
            with open(target_path, "wb") as f:
                for chunk in r_csv.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

            size = target_path.stat().st_size
            sha256_hash = compute_sha256(target_path)
            logger.info(f"FSI Fire CSV downloaded successfully ({size:,} bytes, SHA256: {sha256_hash[:12]}...)")

            return {
                "dataset_id": "fsi_historical_forest_fire",
                "name": f"FSI Historical Forest Fire Points ({state})",
                "filename": target_filename,
                "path": target_path,
                "url": FSI_DOWNLOAD_URL,
                "success": True,
                "status": "SUCCESS",
                "size": size,
                "sha256": sha256_hash,
                "format": "CSV",
                "state": state,
                "temporal_coverage": f"{from_date} to {to_date}",
            }

    except Exception as e:
        logger.error(f"Error downloading FSI Fire data: {e}")

    return {
        "dataset_id": "fsi_historical_forest_fire",
        "name": f"FSI Historical Forest Fire ({state})",
        "filename": target_filename,
        "path": None,
        "url": FSI_DOWNLOAD_URL,
        "success": False,
        "status": "FAILED",
        "size": 0,
        "sha256": None,
        "format": "CSV",
    }


def check_nasa_firms() -> Dict[str, Any]:
    """
    Dataset 13: NASA FIRMS (Fire Information for Resource Management System).
    Checks for NASA_FIRMS_MAP_KEY environment variable.
    If missing, marks as SKIPPED_NO_API_KEY per specification without inventing credentials.
    """
    target_dir = RAW_DIR / "forest_fire" / "nasa_firms"
    target_dir.mkdir(parents=True, exist_ok=True)

    firms_key = os.environ.get("NASA_FIRMS_MAP_KEY")
    if not firms_key:
        logger.info("NASA_FIRMS_MAP_KEY is not configured. Recording SKIPPED_NO_API_KEY.")
        return {
            "dataset_id": "nasa_firms_fire_detections",
            "name": "NASA FIRMS Active Fire Detections (India)",
            "filename": "NONE",
            "path": None,
            "url": "https://firms.modaps.eosdis.nasa.gov/api/area/",
            "success": False,
            "status": "SKIPPED_NO_API_KEY",
            "size": 0,
            "sha256": None,
            "format": "CSV",
            "notes": "Requires free MAP_KEY registered via https://firms.modaps.eosdis.nasa.gov/api/map_key/. Skipped per prompt rule: no credentials invented.",
        }

    # If key was configured, download India area active fires
    api_url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{firms_key}/VIIRS_SNPP_NRT/68,6,98,38/1"
    target_path = target_dir / "nasa_firms_india_active_fires.csv"
    success, status, size, sha256_hash = download_file(
        url=api_url,
        target_path=target_path,
        timeout=60,
    )

    return {
        "dataset_id": "nasa_firms_fire_detections",
        "name": "NASA FIRMS Active Fire Detections (India)",
        "filename": target_path.name if success else "NONE",
        "path": target_path if success else None,
        "url": api_url,
        "success": success,
        "status": status,
        "size": size,
        "sha256": sha256_hash,
        "format": "CSV",
    }


def run_fire_downloads() -> Dict[str, Any]:
    """Orchestrates forest fire dataset downloads (Datasets 12, 13)."""
    logger.info("Starting Forest Fire Datasets Acquisition...")
    res_fsi = download_fsi_historical_fires()
    res_firms = check_nasa_firms()

    return {
        "fsi": res_fsi,
        "firms": res_firms,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_fire_downloads()
