"""
Geographic Administrative Boundaries Acquisition Module.
Handles:
- Dataset 15: India District Boundaries
  - Primary NWDP Official Source (GeoJSON, KML, SHP)
  - Supplementary geoBoundaries ADM2 Open Boundary Dataset
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import requests

from common import download_file, extract_zip, RAW_DIR, compute_sha256
from nwdp_downloader import download_district_boundaries

logger = logging.getLogger("geography_downloader")

GEOBOUNDARIES_API = "https://www.geoboundaries.org/api/current/gbOpen/IND/ADM2/"


def download_geoboundaries_fallback() -> Dict[str, Any]:
    """
    Downloads geoBoundaries ADM2 district boundaries as a supplementary/fallback dataset.
    Preserves separation from NWDP boundaries without overwriting.
    """
    target_dir = RAW_DIR / "geography" / "district_boundaries"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_filename = "geoBoundaries_IND_ADM2.geojson"
    target_path = target_dir / target_filename

    logger.info(f"Querying geoBoundaries API for India ADM2: {GEOBOUNDARIES_API}...")
    try:
        r = requests.get(GEOBOUNDARIES_API, timeout=20)
        if r.status_code != 200:
            logger.error(f"geoBoundaries API query failed: HTTP {r.status_code}")
            return {
                "dataset_id": "geoboundaries_district_boundaries",
                "name": "geoBoundaries India ADM2 District Boundaries",
                "filename": target_filename,
                "path": None,
                "url": GEOBOUNDARIES_API,
                "success": False,
                "status": "FAILED",
                "size": 0,
                "sha256": None,
                "format": "GeoJSON",
            }

        api_meta = r.json()
        gj_url = api_meta.get("gjDownloadURL")
        if not gj_url:
            logger.error("No gjDownloadURL found in geoBoundaries response.")
            return {
                "dataset_id": "geoboundaries_district_boundaries",
                "name": "geoBoundaries India ADM2 District Boundaries",
                "filename": target_filename,
                "path": None,
                "url": GEOBOUNDARIES_API,
                "success": False,
                "status": "FAILED",
                "size": 0,
                "sha256": None,
                "format": "GeoJSON",
            }

        logger.info(f"Downloading geoBoundaries GeoJSON from {gj_url}...")
        success, status, size, sha256_hash = download_file(
            url=gj_url,
            target_path=target_path,
            timeout=180,
        )

        return {
            "dataset_id": "geoboundaries_district_boundaries",
            "name": "geoBoundaries India ADM2 District Boundaries (Supplementary)",
            "filename": target_filename,
            "path": target_path,
            "url": gj_url,
            "success": success,
            "status": status,
            "size": size,
            "sha256": sha256_hash,
            "format": "GeoJSON",
            "boundary_type": "ADM2",
            "is_supplementary": True,
        }

    except Exception as e:
        logger.error(f"Error downloading geoBoundaries: {e}")

    return {
        "dataset_id": "geoboundaries_district_boundaries",
        "name": "geoBoundaries India ADM2 District Boundaries",
        "filename": target_filename,
        "path": None,
        "url": GEOBOUNDARIES_API,
        "success": False,
        "status": "FAILED",
        "size": 0,
        "sha256": None,
        "format": "GeoJSON",
    }


def run_geography_downloads() -> Dict[str, Any]:
    """Orchestrates geographic dataset downloads (Dataset 15)."""
    logger.info("Starting Geographic Administrative Boundaries Acquisition...")
    res_nwdp = download_district_boundaries()
    res_gb = download_geoboundaries_fallback()

    return {
        "nwdp_boundaries": res_nwdp,
        "geoboundaries": res_gb,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_geography_downloads()
