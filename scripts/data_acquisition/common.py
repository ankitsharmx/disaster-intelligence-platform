"""
Common utilities for robust dataset acquisition, streaming downloads,
hash integrity verification, archive extraction, and manifest recording.
"""

import os
import time
import math
import hashlib
import zipfile
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
import requests
import urllib3

# Suppress insecure SSL warnings for government portal root certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger("data_acquisition")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"
REPORTS_DIR = DATA_DIR / "reports"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def compute_sha256(filepath: Path) -> str:
    """Computes SHA-256 checksum of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(65536), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def download_file(
    url: str,
    target_path: Path,
    expected_sha256: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    verify_ssl: bool = False,
    timeout: int = 60,
    max_retries: int = 3,
    chunk_size: int = 65536,
    post_data: Optional[Dict[str, Any]] = None,
    force_redownload: bool = False,
) -> Tuple[bool, str, int, Optional[str]]:
    """
    Downloads a file with streaming, .part temp file, retry backoff, and integrity hashing.
    Returns: (success: bool, status_msg: str, file_size: int, sha256_hex: Optional[str])
    """
    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(target_path.suffix + ".part")

    # 1. Check if final file already exists and passes integrity check
    if target_path.exists() and not force_redownload:
        existing_size = target_path.stat().st_size
        if existing_size > 0:
            existing_hash = compute_sha256(target_path)
            if expected_sha256:
                if existing_hash.lower() == expected_sha256.lower():
                    logger.info(f"File already exists and matches expected SHA-256: {target_path.name}")
                    return True, "EXISTS_VALID", existing_size, existing_hash
            else:
                logger.info(f"File already exists ({existing_size} bytes): {target_path.name}. Skipping re-download.")
                return True, "EXISTS_VALID", existing_size, existing_hash

    req_headers = DEFAULT_HEADERS.copy()
    if headers:
        req_headers.update(headers)

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Downloading [{attempt}/{max_retries}] -> {url} to {target_path.name}...")
            if post_data:
                response = requests.post(
                    url,
                    data=post_data,
                    headers=req_headers,
                    stream=True,
                    timeout=timeout,
                    verify=verify_ssl,
                )
            else:
                response = requests.get(
                    url,
                    headers=req_headers,
                    stream=True,
                    timeout=timeout,
                    verify=verify_ssl,
                )

            if response.status_code not in (200, 206):
                logger.warning(f"HTTP {response.status_code} received from {url}")
                if response.status_code in (401, 403, 404):
                    return False, f"HTTP_{response.status_code}", 0, None
                time.sleep(2 ** attempt)
                continue

            sha256_hash = hashlib.sha256()
            total_bytes = 0

            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        sha256_hash.update(chunk)
                        total_bytes += len(chunk)

            if total_bytes == 0:
                logger.warning(f"Downloaded empty file from {url}")
                if temp_path.exists():
                    temp_path.unlink()
                time.sleep(2 ** attempt)
                continue

            # Atomic rename from .part to final file
            if target_path.exists():
                target_path.unlink()
            temp_path.rename(target_path)

            file_hash = sha256_hash.hexdigest()
            logger.info(f"Successfully downloaded {target_path.name} ({total_bytes:,} bytes, SHA256: {file_hash[:12]}...)")
            return True, "SUCCESS", total_bytes, file_hash

        except Exception as e:
            logger.warning(f"Attempt {attempt} failed for {url}: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass
            time.sleep(2 ** attempt)

    return False, "MAX_RETRIES_EXCEEDED", 0, None


def extract_zip(zip_path: Path, extract_dir: Optional[Path] = None) -> List[Path]:
    """Extracts a ZIP archive into a dedicated directory while retaining the original ZIP."""
    zip_path = Path(zip_path)
    if not zip_path.exists():
        logger.warning(f"ZIP file not found: {zip_path}")
        return []

    if extract_dir is None:
        extract_dir = zip_path.parent / zip_path.stem

    extract_dir.mkdir(parents=True, exist_ok=True)
    extracted_files = []

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)
            for name in zf.namelist():
                p = extract_dir / name
                if p.is_file():
                    extracted_files.append(p)
        logger.info(f"Extracted {len(extracted_files)} files to {extract_dir.name}/")
        return extracted_files
    except Exception as e:
        logger.error(f"Failed extracting {zip_path.name}: {e}")
        return []
