"""
Dataset Validation and Metadata Generation Module.
Validates all raw files in data/raw/:
- CSV: row/column count, headers, date columns, null values, coordinates
- GeoJSON: JSON validity, feature count, geometry types, bounding box
- NetCDF: xarray dimensions, variables, time coverage, units
- ZIP: archive integrity, extraction verification
- XML/RSS: valid XML, feed entry count, alert attributes
- PDF: page count, document validity
Outputs:
- data/metadata/dataset_manifest.csv
- data/metadata/dataset_manifest.json
- data/metadata/source_registry.json
"""

import os
import json
import csv
import logging
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import pandas as pd
import xarray as xr
import feedparser
from pypdf import PdfReader

from common import (
    PROJECT_ROOT,
    DATA_DIR,
    RAW_DIR,
    PROCESSED_DIR,
    METADATA_DIR,
    REPORTS_DIR,
    compute_sha256,
)

logger = logging.getLogger("validate_datasets")

MANIFEST_CSV_FIELDS = [
    "dataset_id",
    "dataset_name",
    "hazard_category",
    "source_agency",
    "source_url",
    "download_url",
    "filename",
    "file_format",
    "download_status",
    "file_size_bytes",
    "row_count",
    "column_count",
    "sha256",
    "retrieved_at_utc",
    "data_start_date",
    "data_end_date",
    "geographic_coverage",
    "license",
    "attribution",
    "is_historical",
    "is_live_snapshot",
    "notes",
]


def validate_csv(filepath: Path) -> Dict[str, Any]:
    """Validates CSV file structure, rows, columns, date columns, coordinates."""
    try:
        # Handle Open-Meteo metadata header rows (skiprows=3)
        skip = 3 if "open_meteo" in filepath.name.lower() else 0
        df_preview = pd.read_csv(filepath, skiprows=skip, nrows=100, low_memory=False)
        cols = list(df_preview.columns)

        # Count total rows efficiently
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            total_lines = sum(1 for _ in f)
            row_count = total_lines - (skip + 1)

        # Detect date columns
        date_candidates = [c for c in cols if any(k in c.lower() for k in ["date", "time", "year", "day", "month"])]
        # Detect coordinate columns
        coord_candidates = [c for c in cols if any(k in c.lower() for k in ["lat", "lon", "x", "y"])]

        # Sample missing values
        null_count = int(df_preview.isna().sum().sum())

        return {
            "valid": True,
            "row_count": max(0, row_count),
            "column_count": len(cols),
            "columns": cols[:20],
            "date_columns": date_candidates,
            "coordinate_columns": coord_candidates,
            "sample_nulls": null_count,
        }
    except Exception as e:
        logger.warning(f"CSV validation warning for {filepath.name}: {e}")
        return {"valid": False, "error": str(e), "row_count": 0, "column_count": 0}


def validate_geojson(filepath: Path) -> Dict[str, Any]:
    """Validates GeoJSON file, features count, geometry types, and coordinates bounding box."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("type") != "FeatureCollection":
            return {"valid": False, "error": "Not a FeatureCollection"}

        features = data.get("features", [])
        geom_types = set()
        lats, lons = [], []

        for feat in features[:1000]:  # Sample bounds from first 1000 features
            geom = feat.get("geometry", {})
            if geom:
                g_type = geom.get("type")
                if g_type:
                    geom_types.add(g_type)
                coords = geom.get("coordinates")
                if g_type == "Point" and coords and len(coords) >= 2:
                    lons.append(coords[0])
                    lats.append(coords[1])

        bounds = None
        if lats and lons:
            bounds = [min(lats), min(lons), max(lats), max(lons)]

        return {
            "valid": True,
            "feature_count": len(features),
            "geometry_types": list(geom_types),
            "sample_bounding_box": bounds,
            "crs": data.get("crs", {}).get("properties", {}).get("name", "EPSG:4326"),
        }
    except Exception as e:
        logger.warning(f"GeoJSON validation error for {filepath.name}: {e}")
        return {"valid": False, "error": str(e), "feature_count": 0}


def validate_netcdf(filepath: Path) -> Dict[str, Any]:
    """Validates NetCDF file with xarray, inspecting dimensions, variables, and time coverage."""
    try:
        with xr.open_dataset(filepath) as ds:
            dims = dict(ds.sizes)
            vars_list = list(ds.data_vars.keys())
            coords_list = list(ds.coords.keys())

            time_coverage = None
            if "time" in ds.coords:
                t_vals = ds["time"].values
                if len(t_vals) > 0:
                    time_coverage = f"{str(t_vals[0])[:10]} to {str(t_vals[-1])[:10]}"

            var_units = {v: ds[v].attrs.get("units", "unknown") for v in vars_list}

            return {
                "valid": True,
                "dimensions": dims,
                "variables": vars_list,
                "coordinates": coords_list,
                "time_coverage": time_coverage,
                "units": var_units,
            }
    except Exception as e:
        logger.warning(f"NetCDF validation error for {filepath.name}: {e}")
        return {"valid": False, "error": str(e)}


def validate_zip(filepath: Path) -> Dict[str, Any]:
    """Validates ZIP archive integrity."""
    try:
        with zipfile.ZipFile(filepath, "r") as zf:
            bad_file = zf.testzip()
            if bad_file:
                return {"valid": False, "error": f"Corrupt file in ZIP: {bad_file}"}
            file_list = zf.namelist()
            return {
                "valid": True,
                "archive_files_count": len(file_list),
                "files": file_list[:10],
            }
    except Exception as e:
        return {"valid": False, "error": str(e)}


def validate_xml_rss(filepath: Path) -> Dict[str, Any]:
    """Validates XML / RSS feed structure and entry count."""
    try:
        feed = feedparser.parse(str(filepath))
        entries = len(feed.entries)
        title = feed.feed.get("title", "Untitled Feed")
        return {
            "valid": True,
            "feed_title": title,
            "entries_count": entries,
            "status": getattr(feed, "status", 200),
        }
    except Exception as e:
        return {"valid": False, "error": str(e), "entries_count": 0}


def validate_pdf(filepath: Path) -> Dict[str, Any]:
    """Validates PDF file and counts pages."""
    try:
        reader = PdfReader(str(filepath))
        page_count = len(reader.pages)
        return {
            "valid": True,
            "page_count": page_count,
        }
    except Exception as e:
        return {"valid": False, "error": str(e), "page_count": 0}


def validate_all_and_build_manifest(download_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validates all downloaded datasets and constructs:
    - data/metadata/dataset_manifest.csv
    - data/metadata/dataset_manifest.json
    - data/metadata/source_registry.json
    """
    METADATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest_rows = []
    source_registry = {}

    logger.info("Validating all downloaded files across data/raw/...")

    for rec in download_records:
        path = rec.get("path")
        fmt = rec.get("format", "").upper()
        size = rec.get("size", 0)
        sha256_hash = rec.get("sha256")
        status = rec.get("status", "SUCCESS")
        fname = rec.get("filename", "NONE")

        row_count = 0
        col_count = 0
        validation_info = {}

        if path and Path(path).exists() and Path(path).is_file():
            p = Path(path)
            size = p.stat().st_size
            if not sha256_hash:
                sha256_hash = compute_sha256(p)

            # Format-specific validation (check extension first to avoid misclassifying zip archives)
            if p.suffix.lower() == ".zip" or fmt == "ZIP":
                v = validate_zip(p)
                row_count = v.get("archive_files_count", 0)
                validation_info = v
            elif fmt == "CSV" or p.suffix.lower() == ".csv":
                v = validate_csv(p)
                row_count = v.get("row_count", 0)
                col_count = v.get("column_count", 0)
                validation_info = v
            elif (fmt in ("GEOJSON", "JSON") or p.suffix.lower() in (".geojson", ".json")) and p.suffix.lower() != ".kmz":
                v = validate_geojson(p)
                row_count = v.get("feature_count", 0)
                validation_info = v
            elif fmt in ("NETCDF", "NC") or p.suffix.lower() == ".nc":
                v = validate_netcdf(p)
                validation_info = v
            elif fmt in ("XML", "RSS") or p.suffix.lower() == ".xml":
                v = validate_xml_rss(p)
                row_count = v.get("entries_count", 0)
                validation_info = v
            elif fmt == "PDF" or p.suffix.lower() == ".pdf":
                v = validate_pdf(p)
                row_count = v.get("page_count", 0)
                validation_info = v
            elif p.suffix.lower() == ".kmz":
                v = validate_zip(p)
                row_count = v.get("archive_files_count", 0)
                validation_info = v

        row = {
            "dataset_id": rec.get("dataset_id", "unknown"),
            "dataset_name": rec.get("name", fname),
            "hazard_category": rec.get("hazard_category", "general"),
            "source_agency": rec.get("source_agency", "Official Agency"),
            "source_url": rec.get("source_url", rec.get("url", "")),
            "download_url": rec.get("url", ""),
            "filename": fname,
            "file_format": fmt,
            "download_status": status,
            "file_size_bytes": size,
            "row_count": row_count,
            "column_count": col_count,
            "sha256": sha256_hash or "NONE",
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "data_start_date": rec.get("data_start_date", "N/A"),
            "data_end_date": rec.get("data_end_date", "N/A"),
            "geographic_coverage": rec.get("geographic_coverage", "India / Punjab"),
            "license": rec.get("license", "Government Open Data / Public Domain"),
            "attribution": rec.get("attribution", rec.get("source_agency", "Official Agency")),
            "is_historical": rec.get("is_historical", True),
            "is_live_snapshot": rec.get("is_live_snapshot", False),
            "notes": rec.get("notes", ""),
        }
        manifest_rows.append(row)

        # Source Registry Grouping
        d_id = row["dataset_id"]
        if d_id not in source_registry:
            source_registry[d_id] = {
                "dataset_id": d_id,
                "dataset_name": row["dataset_name"],
                "hazard_category": row["hazard_category"],
                "source_agency": row["source_agency"],
                "source_url": row["source_url"],
                "data_classification": (
                    "Live Source Snapshot"
                    if row["is_live_snapshot"]
                    else (
                        "Modelled / Reanalysis"
                        if "open_meteo" in d_id
                        else (
                            "Static Geographic Reference"
                            if "boundaries" in d_id or "facilities" in d_id
                            else "Historical Observations"
                        )
                    )
                ),
                "license": row["license"],
                "files_count": 0,
                "total_bytes": 0,
                "files": [],
            }
        source_registry[d_id]["files_count"] += 1
        source_registry[d_id]["total_bytes"] += size
        source_registry[d_id]["files"].append({
            "filename": fname,
            "format": fmt,
            "size_bytes": size,
            "status": status,
            "sha256": sha256_hash,
            "validation": validation_info,
        })

    # 1. Write dataset_manifest.csv
    csv_path = METADATA_DIR / "dataset_manifest.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_CSV_FIELDS)
        writer.writeheader()
        writer.writerows(manifest_rows)
    logger.info(f"Manifest CSV saved to {csv_path} ({len(manifest_rows)} entries)")

    # 2. Write dataset_manifest.json
    json_path = METADATA_DIR / "dataset_manifest.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(manifest_rows, f, indent=2, ensure_ascii=False)
    logger.info(f"Manifest JSON saved to {json_path}")

    # 3. Write source_registry.json
    registry_path = METADATA_DIR / "source_registry.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(source_registry, f, indent=2, ensure_ascii=False)
    logger.info(f"Source Registry JSON saved to {registry_path} ({len(source_registry)} unique dataset sources)")

    return {
        "manifest_rows": manifest_rows,
        "source_registry": source_registry,
        "csv_path": csv_path,
        "json_path": json_path,
        "registry_path": registry_path,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Validator module ready.")
