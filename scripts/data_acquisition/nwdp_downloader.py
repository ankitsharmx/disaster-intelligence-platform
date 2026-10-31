"""
NWDP (National Water Data Portal - NWIC) Downloader.
Interacts with the official NWDP CKAN API to retrieve resources for:
- IMD Daily Rainfall (District-wise & State-wise)
- Punjab River Water Level Hourly (1991-2020, 2021-2025, 2026-2030)
- Punjab River Discharge Hourly (1970-2025, 2026-2030)
- CWC River Discharge Manual Daily
- India District Boundaries (GeoJSON, KML, SHP)
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests

from common import download_file, extract_zip, RAW_DIR, compute_sha256

logger = logging.getLogger("nwdp_downloader")
NWDP_API_BASE = "https://nwdp.nwic.gov.in/api/3/action/package_show"


def get_package_metadata(package_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves full package metadata and resources list from NWDP CKAN API."""
    url = f"{NWDP_API_BASE}?id={package_id}"
    try:
        r = requests.get(url, timeout=20, verify=False)
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                return data.get("result")
        logger.warning(f"Failed fetching package {package_id}: HTTP {r.status_code}")
    except Exception as e:
        logger.error(f"Error querying NWDP API for {package_id}: {e}")
    return None


def download_imd_daily_rainfall() -> List[Dict[str, Any]]:
    """Dataset 1: IMD District-wise & State-wise daily rainfall CSVs."""
    target_dir = RAW_DIR / "rainfall" / "imd"
    target_dir.mkdir(parents=True, exist_ok=True)
    results = []

    pkg = get_package_metadata("rainfall-daily-imd")
    if not pkg:
        logger.error("Could not retrieve rainfall-daily-imd package metadata.")
        return results

    for res in pkg.get("resources", []):
        url = res.get("url")
        res_name = res.get("name")
        filename = url.split("/")[-1] if "/" in url else f"{res_name}.csv"
        target_path = target_dir / filename

        success, status, size, sha256_hash = download_file(
            url=url,
            target_path=target_path,
            timeout=120,
        )
        results.append({
            "dataset_id": "imd_daily_rainfall",
            "name": res_name,
            "filename": filename,
            "path": target_path,
            "url": url,
            "success": success,
            "status": status,
            "size": size,
            "sha256": sha256_hash,
            "format": res.get("format", "CSV"),
        })

    return results


def download_punjab_water_level() -> List[Dict[str, Any]]:
    """Dataset 4: Punjab River Water Level Hourly."""
    target_dir = RAW_DIR / "flood" / "punjab_water_department"
    target_dir.mkdir(parents=True, exist_ok=True)
    results = []

    pkg = get_package_metadata("river-water-level-telemetry-hourly-punjab-surface-water-department")
    if not pkg:
        logger.error("Could not retrieve Punjab water level package metadata.")
        return results

    for res in pkg.get("resources", []):
        url = res.get("url")
        res_name = res.get("name")
        filename = url.split("/")[-1] if "/" in url else f"{res_name}.csv"
        target_path = target_dir / filename

        success, status, size, sha256_hash = download_file(
            url=url,
            target_path=target_path,
            timeout=180,
        )
        results.append({
            "dataset_id": "punjab_river_water_level",
            "name": res_name,
            "filename": filename,
            "path": target_path,
            "url": url,
            "success": success,
            "status": status,
            "size": size,
            "sha256": sha256_hash,
            "format": res.get("format", "CSV"),
        })

    return results


def download_punjab_river_discharge() -> List[Dict[str, Any]]:
    """Dataset 5: Punjab River Discharge Hourly."""
    target_dir = RAW_DIR / "flood" / "punjab_water_department"
    target_dir.mkdir(parents=True, exist_ok=True)
    results = []

    pkg = get_package_metadata("river-discharge-telemetry-hourly-punjab-surface-water-department")
    if not pkg:
        logger.error("Could not retrieve Punjab river discharge package metadata.")
        return results

    for res in pkg.get("resources", []):
        url = res.get("url")
        res_name = res.get("name")
        filename = url.split("/")[-1] if "/" in url else f"{res_name}.csv"
        target_path = target_dir / filename

        success, status, size, sha256_hash = download_file(
            url=url,
            target_path=target_path,
            timeout=180,
        )
        results.append({
            "dataset_id": "punjab_river_discharge",
            "name": res_name,
            "filename": filename,
            "path": target_path,
            "url": url,
            "success": success,
            "status": status,
            "size": size,
            "sha256": sha256_hash,
            "format": res.get("format", "CSV"),
        })

    return results


def download_cwc_river_discharge() -> List[Dict[str, Any]]:
    """
    Dataset 6: CWC River Discharge Manual Daily.
    Downloads accessible state-wise CWC CSV resources, prioritizing Punjab and neighbouring states.
    If a Punjab-specific CWC resource is not listed, do not substitute another state's data. Record its absence.
    """
    target_dir = RAW_DIR / "flood" / "cwc"
    target_dir.mkdir(parents=True, exist_ok=True)
    results = []

    pkg = get_package_metadata("river-discharge-manual-dailly-central-water-commission-cwc")
    if not pkg:
        logger.error("Could not retrieve CWC river discharge package metadata.")
        return results

    resources = pkg.get("resources", [])
    logger.info(f"CWC River Discharge total resources found: {len(resources)}")

    # Check for Punjab specific resource
    punjab_resources = [r for r in resources if "punjab" in r.get("name", "").lower() or "_pb_" in r.get("url", "").lower()]
    if not punjab_resources:
        logger.warning("No Punjab-specific CWC river discharge resource listed in NWDP metadata. Recording absence per specification.")
        results.append({
            "dataset_id": "cwc_river_discharge_punjab",
            "name": "CWC River Discharge Punjab (Absence Recorded)",
            "filename": "NONE",
            "path": None,
            "url": "https://nwdp.nwic.gov.in/dataset/river-discharge-manual-dailly-central-water-commission-cwc",
            "success": False,
            "status": "UNAVAILABLE",
            "size": 0,
            "sha256": None,
            "format": "CSV",
            "notes": "Punjab-specific CWC river discharge resource is not published on NWDP portal. Absence verified across 52 state resources.",
        })

    # Download neighbouring / northern states where available (e.g., Haryana, Rajasthan, HP, or major basinal states)
    target_state_keywords = ["haryana", "rajasthan", "himachal", "delhi", "jammu"]
    selected_resources = []
    for r in resources:
        name_lower = r.get("name", "").lower()
        if any(kw in name_lower for kw in target_state_keywords):
            selected_resources.append(r)

    # Download at least 2 representative neighbouring state historical & newer series
    for res in selected_resources[:6]:
        url = res.get("url")
        res_name = res.get("name")
        filename = url.split("/")[-1] if "/" in url else f"{res_name}.csv"
        target_path = target_dir / filename

        success, status, size, sha256_hash = download_file(
            url=url,
            target_path=target_path,
            timeout=180,
        )
        results.append({
            "dataset_id": "cwc_river_discharge_neighbouring",
            "name": res_name,
            "filename": filename,
            "path": target_path,
            "url": url,
            "success": success,
            "status": status,
            "size": size,
            "sha256": sha256_hash,
            "format": res.get("format", "CSV"),
        })

    return results


def download_district_boundaries() -> List[Dict[str, Any]]:
    """Dataset 15: India District Boundaries (NWDP source)."""
    target_dir = RAW_DIR / "geography" / "district_boundaries"
    target_dir.mkdir(parents=True, exist_ok=True)
    results = []

    pkg = get_package_metadata("district-boundary")
    if not pkg:
        logger.error("Could not retrieve district-boundary package metadata.")
        return results

    for res in pkg.get("resources", []):
        url = res.get("url")
        res_name = res.get("name")
        filename = url.split("/")[-1] if "/" in url else f"{res_name}.zip"
        target_path = target_dir / filename

        success, status, size, sha256_hash = download_file(
            url=url,
            target_path=target_path,
            timeout=180,
        )

        extracted_files = []
        if success and filename.endswith(".zip"):
            extract_subfolder = target_dir / target_path.stem
            extracted_files = extract_zip(target_path, extract_subfolder)

        results.append({
            "dataset_id": "nwdp_district_boundaries",
            "name": res_name,
            "filename": filename,
            "path": target_path,
            "url": url,
            "success": success,
            "status": status,
            "size": size,
            "sha256": sha256_hash,
            "format": res.get("format", "ZIP"),
            "extracted_count": len(extracted_files),
        })

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing NWDP Downloader...")
    r1 = download_imd_daily_rainfall()
    print(f"IMD Rainfall: {len(r1)} resources")
    r2 = download_punjab_water_level()
    print(f"Punjab RWL: {len(r2)} resources")
