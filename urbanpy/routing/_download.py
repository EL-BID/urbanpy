"""Atomic, safely resumable Geofabrik PBF downloads."""

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import urlparse

import requests

from urbanpy.errors import UrbanPyError
from urbanpy.geofabrik import USER_AGENT

DEFAULT_MAX_PBF_BYTES: Final = 25 * 1024 * 1024 * 1024


class DownloadError(UrbanPyError):
    """A PBF download failed or violated a safety constraint."""


@dataclass(frozen=True, slots=True)
class DownloadResult:
    path: Path
    size: int
    sha256: str
    etag: str | None
    last_modified: str | None


def download_pbf(
    url: str,
    target: Path,
    *,
    session: requests.Session | None = None,
    timeout: tuple[float, float] = (5.0, 120.0),
    max_bytes: int = DEFAULT_MAX_PBF_BYTES,
    chunk_size: int = 1024 * 1024,
) -> DownloadResult:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "download.geofabrik.de":
        raise DownloadError("PBF source must be an official Geofabrik HTTPS URL.")

    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(f"{target.name}.part")
    metadata_path = target.with_name(f"{target.name}.part.json")
    metadata = _read_metadata(metadata_path)
    offset = part.stat().st_size if part.exists() and metadata.get("url") == url else 0
    if offset > max_bytes:
        raise DownloadError("Existing partial PBF exceeds the configured size limit.")

    headers = {"Accept": "application/octet-stream", "User-Agent": USER_AGENT}
    if offset:
        headers["Range"] = f"bytes={offset}-"
        validator = metadata.get("etag") or metadata.get("last_modified")
        if isinstance(validator, str):
            headers["If-Range"] = validator

    client = session or requests.Session()
    try:
        response = client.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
    except requests.RequestException as error:
        raise DownloadError("Could not download the Geofabrik PBF.") from error

    append = offset > 0 and response.status_code == 206
    if not append:
        offset = 0
    etag = response.headers.get("ETag")
    last_modified = response.headers.get("Last-Modified")
    _write_metadata(
        metadata_path,
        {"url": url, "etag": etag, "last_modified": last_modified},
    )

    mode = "ab" if append else "wb"
    size = offset
    try:
        with part.open(mode) as destination:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                size += len(chunk)
                if size > max_bytes:
                    raise DownloadError("PBF exceeds the configured size limit.")
                destination.write(chunk)
            destination.flush()
            os.fsync(destination.fileno())
    except OSError as error:
        raise DownloadError(f"Could not write PBF download to {part}.") from error

    digest = sha256_file(part)
    os.replace(part, target)
    metadata_path.unlink(missing_ok=True)
    return DownloadResult(target, size, digest, etag, last_modified)


def sha256_file(path: Path) -> str:
    """Hash a potentially large file without loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_metadata(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def _write_metadata(path: Path, value: dict[str, object]) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


__all__ = ["DownloadError", "DownloadResult", "download_pbf", "sha256_file"]
