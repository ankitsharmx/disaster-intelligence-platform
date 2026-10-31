"""
Cyclone Data Acquisition Module.
Handles:
- Dataset 11: NOAA IBTrACS v04r01 North Indian Ocean (NI) Cyclone Track CSV
- Technical Documentation & Variable Descriptions PDF
- Column Documentation PDF
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

from common import download_file, RAW_DIR, compute_sha256

logger = logging.getLogger("cyclone_downloader")

IBTRACS_NI_CSV_URL = (
    "https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/ibtracs.NI.list.v04r01.csv"
)
IBTRACS_COLUMN_DOC_URL = (
    "https://www.ncei.noaa.gov/sites/default/files/2025-09/IBTrACS_v04r01_column_documentation.pdf"
)
IBTRACS_TECH_DOC_URL = (
    "https://www.ncei.noaa.gov/sites/default/files/2025-04/IBTrACS_version4r01_Technical_Details.pdf"
)


def download_noaa_ibtracs() -> List[Dict[str, Any]]:
    """
    Dataset 11: NOAA IBTrACS North Indian Ocean (NI) cyclone track records.
    Downloads the official v04r01 basin CSV and associated variable description documents.
    """
    target_dir = RAW_DIR / "cyclone" / "noaa_ibtracs"
    target_dir.mkdir(parents=True, exist_ok=True)
    results = []

    files_to_download = [
        ("ibtracs.NI.list.v04r01.csv", IBTRACS_NI_CSV_URL, "CSV"),
        ("IBTrACS_v04r01_column_documentation.pdf", IBTRACS_COLUMN_DOC_URL, "PDF"),
        ("IBTrACS_version4r01_Technical_Details.pdf", IBTRACS_TECH_DOC_URL, "PDF"),
    ]

    for filename, url, fmt in files_to_download:
        target_path = target_dir / filename
        logger.info(f"Downloading NOAA IBTrACS resource: {filename}...")
        success, status, size, sha256_hash = download_file(
            url=url,
            target_path=target_path,
            timeout=180,
        )

        results.append({
            "dataset_id": "noaa_ibtracs_north_indian_ocean",
            "name": f"NOAA IBTrACS v04r01 ({filename})",
            "filename": filename,
            "path": target_path,
            "url": url,
            "success": success,
            "status": status,
            "size": size,
            "sha256": sha256_hash,
            "format": fmt,
            "basin": "North Indian Ocean (NI)",
            "version": "v04r01",
        })

    return results


def run_cyclone_downloads() -> Dict[str, Any]:
    """Orchestrates cyclone dataset downloads (Dataset 11)."""
    logger.info("Starting Cyclone Datasets Acquisition...")
    res = download_noaa_ibtracs()
    return {"ibtracs": res}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_cyclone_downloads()
