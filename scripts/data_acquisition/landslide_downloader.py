"""
Landslide Data Acquisition Module.
Handles:
- Dataset 9: NASA Global Landslide Catalog Export (Historical through 2016-03-07)
- Dataset 10: ISRO Landslide Atlas of India (2023 Official Published Report PDF)
"""

import logging
from pathlib import Path
from typing import Dict, Any, List
import requests

from common import download_file, RAW_DIR, compute_sha256

logger = logging.getLogger("landslide_downloader")

NASA_LANDSLIDE_URLS = [
    "https://data.nasa.gov/docs/legacy/Global_Landslide_Catalog_Export/Global_Landslide_Catalog_Export_rows.csv",
    "https://raw.githubusercontent.com/AntoineSueur/Geoplot-landslides/master/Global_Landslide_Catalog_Export.csv",
]

ISRO_LANDSLIDE_PDF_URL = "https://www.isro.gov.in/media_isro/pdf/LandslideAtlas_new_2023.pdf"


def download_nasa_landslide_catalog() -> Dict[str, Any]:
    """
    Dataset 9: NASA Global Landslide Catalog Export CSV.
    Coverage is historical and officially documented through 2016-03-07.
    """
    target_dir = RAW_DIR / "landslide" / "nasa"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "Global_Landslide_Catalog_Export.csv"

    logger.info("Downloading NASA Global Landslide Catalog Export...")
    success = False
    status = "FAILED"
    size = 0
    sha256_hash = None
    used_url = NASA_LANDSLIDE_URLS[0]

    for url in NASA_LANDSLIDE_URLS:
        try:
            logger.info(f"Attempting download from {url}...")
            # For data.nasa.gov, check if head provides direct S3 redirect
            actual_url = url
            if "data.nasa.gov" in url:
                try:
                    r_head = requests.head(url, allow_redirects=False, timeout=10)
                    loc = r_head.headers.get("Location")
                    if loc:
                        actual_url = loc
                except Exception:
                    pass

            success, status, size, sha256_hash = download_file(
                url=actual_url,
                target_path=target_path,
                timeout=90,
            )
            if success:
                used_url = url
                break
        except Exception as e:
            logger.warning(f"Failed from {url}: {e}")

    return {
        "dataset_id": "nasa_global_landslide_catalog",
        "name": "NASA Global Landslide Catalog Export",
        "filename": target_path.name,
        "path": target_path,
        "url": used_url,
        "success": success,
        "status": status,
        "size": size,
        "sha256": sha256_hash,
        "format": "CSV",
        "is_historical": True,
        "temporal_coverage": "2007-01-01 to 2016-03-07",
        "notes": "Historical export ending 2016-03-07. Succeeded by NASA COOLR program.",
    }


def download_isro_landslide_atlas() -> Dict[str, Any]:
    """
    Dataset 10: ISRO Landslide Atlas of India (2023 Official Published Report PDF).
    Published by National Remote Sensing Centre (NRSC) / ISRO.
    """
    target_dir = RAW_DIR / "landslide" / "isro"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / "LandslideAtlas_new_2023.pdf"

    logger.info("Downloading ISRO Landslide Atlas of India PDF...")
    success, status, size, sha256_hash = download_file(
        url=ISRO_LANDSLIDE_PDF_URL,
        target_path=target_path,
        timeout=180,
    )

    return {
        "dataset_id": "isro_landslide_atlas",
        "name": "ISRO Landslide Atlas of India (2023)",
        "filename": target_path.name,
        "path": target_path,
        "url": ISRO_LANDSLIDE_PDF_URL,
        "success": success,
        "status": status,
        "size": size,
        "sha256": sha256_hash,
        "format": "PDF",
        "is_historical": True,
        "notes": "Official 2023 published atlas by NRSC/ISRO detailing national landslide database and district vulnerability rankings.",
    }


def run_landslide_downloads() -> Dict[str, Any]:
    """Orchestrates landslide dataset downloads (Datasets 9, 10)."""
    logger.info("Starting Landslide Datasets Acquisition...")
    res_nasa = download_nasa_landslide_catalog()
    res_isro = download_isro_landslide_atlas()

    return {
        "nasa_landslide": res_nasa,
        "isro_landslide": res_isro,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_landslide_downloads()
