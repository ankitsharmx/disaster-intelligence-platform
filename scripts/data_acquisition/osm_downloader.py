"""
OpenStreetMap Emergency Facilities Acquisition Module.
Handles:
- Dataset 16: OpenStreetMap critical and emergency facilities for Punjab:
  Hospitals, Clinics, Shelters, Police stations, Fire stations, Emergency assembly points.
Transforms Overpass response into valid GeoJSON with full attribution.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import requests

from common import RAW_DIR, compute_sha256

logger = logging.getLogger("osm_downloader")

OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

PUNJAB_FACILITIES_QUERY = """
[out:json][timeout:90];
area["ISO3166-2"="IN-PB"]["admin_level"="4"]->.searchArea;
(
  node["amenity"="hospital"](area.searchArea);
  node["amenity"="clinic"](area.searchArea);
  node["amenity"="police"](area.searchArea);
  node["amenity"="fire_station"](area.searchArea);
  node["amenity"="shelter"](area.searchArea);
  node["emergency"="assembly_point"](area.searchArea);
  way["amenity"="hospital"](area.searchArea);
  way["amenity"="police"](area.searchArea);
  way["amenity"="fire_station"](area.searchArea);
  way["amenity"="shelter"](area.searchArea);
);
out center;
"""


def download_osm_punjab_facilities() -> Dict[str, Any]:
    """
    Dataset 16: Downloads Punjab critical facilities from OpenStreetMap via Overpass API.
    Extracts hospitals, clinics, police, fire stations, shelters, and assembly points.
    Saves standard GeoJSON FeatureCollection with attribution.
    """
    target_dir = RAW_DIR / "facilities" / "openstreetmap"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_filename = "osm_punjab_emergency_facilities.geojson"
    target_path = target_dir / target_filename

    # If already downloaded and valid, return EXISTS_VALID
    if target_path.exists() and target_path.stat().st_size > 1000:
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                existing_gj = json.load(f)
            feat_count = len(existing_gj.get("features", []))
            sz = target_path.stat().st_size
            sha = compute_sha256(target_path)
            logger.info(f"OSM facilities dataset already exists ({feat_count} features, {sz:,} bytes). Skipping Overpass query.")
            return {
                "dataset_id": "osm_punjab_emergency_facilities",
                "name": "OpenStreetMap Punjab Emergency Facilities",
                "filename": target_filename,
                "path": target_path,
                "url": "https://www.openstreetmap.org/",
                "success": True,
                "status": "EXISTS_VALID",
                "size": sz,
                "sha256": sha,
                "format": "GeoJSON",
                "feature_count": feat_count,
                "category_summary": existing_gj.get("category_summary", {}),
                "attribution": "© OpenStreetMap contributors, ODbL 1.0",
            }
        except Exception as e:
            logger.warning(f"Existing OSM file failed validation ({e}), re-querying Overpass...")

    logger.info("Executing Overpass query for Punjab emergency facilities...")

    elements = []
    used_server = OVERPASS_SERVERS[0]
    success = False

    for srv in OVERPASS_SERVERS:
        try:
            logger.info(f"Querying Overpass server: {srv}...")
            r = requests.post(
                srv,
                data={"data": PUNJAB_FACILITIES_QUERY},
                headers={"User-Agent": "AntigravityDisasterPlatform/1.0 (contact: admin@disastermgmt.gov)"},
                timeout=120,
            )
            if r.status_code == 200:
                data = r.json()
                elements = data.get("elements", [])
                logger.info(f"Retrieved {len(elements)} raw facility elements from OSM.")
                used_server = srv
                success = True
                break
            else:
                logger.warning(f"Overpass server {srv} returned HTTP {r.status_code}")
        except Exception as e:
            logger.warning(f"Error querying {srv}: {e}")

    if not success or not elements:
        logger.error("Failed retrieving OSM facilities from Overpass servers.")
        return {
            "dataset_id": "osm_punjab_emergency_facilities",
            "name": "OpenStreetMap Punjab Emergency Facilities",
            "filename": target_filename,
            "path": None,
            "url": used_server,
            "success": False,
            "status": "FAILED",
            "size": 0,
            "sha256": None,
            "format": "GeoJSON",
        }

    # Convert Overpass elements into GeoJSON FeatureCollection
    features = []
    category_counts = {}

    for elem in elements:
        tags = elem.get("tags", {})
        amenity = tags.get("amenity")
        emergency = tags.get("emergency")
        category = amenity or emergency or "facility"

        category_counts[category] = category_counts.get(category, 0) + 1

        # Coordinate resolution: node vs way center
        lat = elem.get("lat")
        lon = elem.get("lon")
        if lat is None or lon is None:
            center = elem.get("center", {})
            lat = center.get("lat")
            lon = center.get("lon")

        if lat is None or lon is None:
            continue

        feat = {
            "type": "Feature",
            "id": f"{elem.get('type')}/{elem.get('id')}",
            "geometry": {
                "type": "Point",
                "coordinates": [float(lon), float(lat)],
            },
            "properties": {
                "osm_id": elem.get("id"),
                "osm_type": elem.get("type"),
                "category": category,
                "amenity": amenity,
                "emergency": emergency,
                "name": tags.get("name"),
                "name_en": tags.get("name:en"),
                "operator": tags.get("operator"),
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "capacity": tags.get("capacity"),
                "addr_city": tags.get("addr:city"),
                "addr_district": tags.get("addr:district"),
                "tags": tags,
            },
        }
        features.append(feat)

    geojson_doc = {
        "type": "FeatureCollection",
        "attribution": "© OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright)",
        "generator": "Overpass API via Antigravity Disaster Management Platform",
        "region": "Punjab, India",
        "total_features": len(features),
        "category_summary": category_counts,
        "features": features,
    }

    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(geojson_doc, f, indent=2, ensure_ascii=False)

    size = target_path.stat().st_size
    sha256_hash = compute_sha256(target_path)
    logger.info(f"OSM GeoJSON saved successfully ({len(features)} features, {size:,} bytes, SHA256: {sha256_hash[:12]}...)")

    return {
        "dataset_id": "osm_punjab_emergency_facilities",
        "name": "OpenStreetMap Punjab Emergency Facilities",
        "filename": target_filename,
        "path": target_path,
        "url": used_server,
        "success": True,
        "status": "SUCCESS",
        "size": size,
        "sha256": sha256_hash,
        "format": "GeoJSON",
        "feature_count": len(features),
        "category_summary": category_counts,
        "attribution": "© OpenStreetMap contributors, ODbL 1.0",
    }


def run_osm_downloads() -> Dict[str, Any]:
    """Orchestrates OSM dataset download (Dataset 16)."""
    logger.info("Starting OpenStreetMap Facilities Acquisition...")
    res = download_osm_punjab_facilities()
    return {"osm_facilities": res}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_osm_downloads()
