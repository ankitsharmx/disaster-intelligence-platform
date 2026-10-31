"""
Official Multi-Hazard Alerts Acquisition Module.
Handles:
- Dataset 14: NDMA Sachet Common Alerting Protocol (CAP) RSS Feeds
  - All India Feed: https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml
  - Punjab Feed: https://sachet.ndma.gov.in/cap_public_website/rss/rss_punjab.xml
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import feedparser
import requests

from common import download_file, RAW_DIR, PROCESSED_DIR, compute_sha256

logger = logging.getLogger("alerts_downloader")

SACHET_FEEDS = {
    "all_india": {
        "url": "https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml",
        "raw_filename": "ndma_sachet_rss_india.xml",
        "name": "NDMA Sachet All India Alert Feed",
    },
    "punjab": {
        "url": "https://sachet.ndma.gov.in/cap_public_website/rss/rss_punjab.xml",
        "raw_filename": "ndma_sachet_rss_punjab.xml",
        "name": "NDMA Sachet Punjab Regional Alert Feed",
    },
}


def parse_sachet_feed_entries(raw_xml_path: Path) -> List[Dict[str, Any]]:
    """
    Parses downloaded CAP RSS feed to extract standardized alert attributes:
    - Alert title
    - Hazard category
    - Issuing authority
    - Affected location
    - Publication timestamp
    - Expiration or validity time
    - Original alert URL
    - Instructions / description
    """
    parsed_alerts = []
    if not raw_xml_path.exists():
        return parsed_alerts

    feed = feedparser.parse(str(raw_xml_path))
    for entry in feed.entries:
        # Extract fields faithfully without inventing missing data
        title = entry.get("title", "")
        summary = entry.get("summary", "") or entry.get("description", "")
        link = entry.get("link", "")
        published = entry.get("published", "") or entry.get("updated", "")
        author = entry.get("author", "") or entry.get("publisher", "NDMA / State Disaster Management")
        category = entry.get("category", "") or entry.get("tags", [{}])[0].get("term", "") if entry.get("tags") else ""

        # Check for CAP-specific tags if embedded in entry
        expires = entry.get("expires", "")
        area_desc = entry.get("area_desc", "") or entry.get("georss_point", "")

        parsed_alerts.append({
            "title": title,
            "hazard_category": category,
            "issuing_authority": author,
            "affected_location": area_desc,
            "published_at": published,
            "expires_at": expires,
            "alert_url": link,
            "instructions": summary,
        })

    return parsed_alerts


def download_ndma_sachet_alerts() -> List[Dict[str, Any]]:
    """Downloads raw RSS XML snapshots for All India and Punjab feeds."""
    raw_dir = RAW_DIR / "alerts" / "ndma_sachet"
    processed_dir = PROCESSED_DIR / "alerts"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for feed_key, feed_meta in SACHET_FEEDS.items():
        url = feed_meta["url"]
        fname = feed_meta["raw_filename"]
        target_path = raw_dir / fname

        logger.info(f"Downloading NDMA Sachet feed: {feed_meta['name']}...")
        success, status, size, sha256_hash = download_file(
            url=url,
            target_path=target_path,
            timeout=45,
        )

        entries_count = 0
        if success:
            parsed = parse_sachet_feed_entries(target_path)
            entries_count = len(parsed)
            # Save parsed JSON snapshot in processed/alerts
            json_target = processed_dir / f"ndma_sachet_alerts_{feed_key}.json"
            with open(json_target, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            logger.info(f"Parsed {entries_count} active alert items from {fname}.")

        results.append({
            "dataset_id": f"ndma_sachet_{feed_key}",
            "name": feed_meta["name"],
            "filename": fname,
            "path": target_path,
            "url": url,
            "success": success,
            "status": status,
            "size": size,
            "sha256": sha256_hash,
            "format": "XML",
            "is_live_snapshot": True,
            "entries_count": entries_count,
        })

    return results


def run_alerts_downloads() -> Dict[str, Any]:
    """Orchestrates multi-hazard alerts acquisition (Dataset 14)."""
    logger.info("Starting Multi-Hazard Alerts Acquisition...")
    res = download_ndma_sachet_alerts()
    return {"sachet_feeds": res}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_alerts_downloads()
