"""
Flood and River Data Acquisition Module.
Handles:
- Dataset 4: Punjab River Water Level — Hourly (NWDP)
- Dataset 5: Punjab River Discharge — Hourly (NWDP)
- Dataset 6: CWC River Discharge — Daily (NWDP)
- Dataset 7: India Flood Inventory — IIT Delhi (Zenodo Version 4)
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import requests

from common import download_file, RAW_DIR, compute_sha256
from nwdp_downloader import (
    download_punjab_water_level,
    download_punjab_river_discharge,
    download_cwc_river_discharge,
)

logger = logging.getLogger("flood_downloader")
ZENODO_RECORD_API = "https://zenodo.org/api/records/16994648"


def download_iit_delhi_flood_inventory() -> List[Dict[str, Any]]:
    """
    Dataset 7: India Flood Inventory - Impacts (IFI-Impacts) [1967-2023] by IIT Delhi.
    Downloads all Version 4 files directly via Zenodo REST API:
    - DFSI.csv
    - District_FloodedArea.csv
    - District_FloodImpact.csv
    - India_Flood_Inventory_v3.csv
    """
    target_dir = RAW_DIR / "flood" / "india_flood_inventory"
    target_dir.mkdir(parents=True, exist_ok=True)
    results = []

    logger.info(f"Querying Zenodo API for India Flood Inventory: {ZENODO_RECORD_API}...")
    try:
        r = requests.get(ZENODO_RECORD_API, timeout=25)
        if r.status_code != 200:
            logger.error(f"Failed querying Zenodo API: HTTP {r.status_code}")
            return results

        record_data = r.json()
        files = record_data.get("files", [])
        logger.info(f"Found {len(files)} files in Zenodo record 16994648.")

        for f_meta in files:
            filename = f_meta.get("key")
            download_url = f_meta.get("links", {}).get("self")
            expected_size = f_meta.get("size")
            target_path = target_dir / filename

            success, status, size, sha256_hash = download_file(
                url=download_url,
                target_path=target_path,
                timeout=180,
            )

            results.append({
                "dataset_id": "iit_delhi_flood_inventory",
                "name": f"India Flood Inventory - {filename}",
                "filename": filename,
                "path": target_path,
                "url": download_url,
                "success": success,
                "status": status,
                "size": size,
                "expected_size": expected_size,
                "sha256": sha256_hash,
                "format": "CSV",
            })

    except Exception as e:
        logger.error(f"Error downloading IIT Delhi Flood Inventory: {e}")

    return results


def run_flood_downloads() -> Dict[str, Any]:
    """Orchestrates all flood and river discharge downloads (Datasets 4, 5, 6, 7)."""
    logger.info("Starting Flood & River Datasets Acquisition...")
    res_rwl = download_punjab_water_level()
    res_q_pb = download_punjab_river_discharge()
    res_cwc = download_cwc_river_discharge()
    res_iitd = download_iit_delhi_flood_inventory()

    return {
        "punjab_water_level": res_rwl,
        "punjab_river_discharge": res_q_pb,
        "cwc_river_discharge": res_cwc,
        "iit_delhi_flood_inventory": res_iitd,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_flood_downloads()
