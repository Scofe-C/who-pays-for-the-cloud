"""Shared helpers for fetch_*.py: dated raw paths, write-once, .env access."""

from __future__ import annotations

import datetime as dt
import logging
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TODAY = dt.date.today().isoformat()
# Generic client id for public sites that need no contact header (Census, EIA, BLS).
GENERIC_UA = "IE6600-course-project-data-pipeline/1.0"

log = logging.getLogger("fetch")


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def env(name: str) -> str:
    """Read a secret from .env; fail loud if missing. Never log the value."""
    val = (dotenv_values(ROOT / ".env").get(name) or "").strip()
    if not val:
        log.error("%s missing in .env", name)
        sys.exit(2)
    return val


def raw_path(subdir: str, stem: str, suffix: str) -> Path:
    """data/raw/<subdir>/<stem>_<YYYY-MM-DD><suffix>. Filename carries the download date."""
    d = RAW / subdir if subdir else RAW
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{stem}_{TODAY}{suffix}"


def write_once(path: Path, content: bytes, secrets: tuple[str, ...] = ()) -> bool:
    """Write a raw file once; never overwrite (data/raw is read-only after download)."""
    for s in secrets:
        if s.encode("utf-8") in content:
            log.error("refusing to write %s: response contains a secret", path.name)
            sys.exit(3)
    if path.exists():
        log.info("exists, not overwritten: %s", path.relative_to(ROOT))
        return False
    path.write_bytes(content)
    log.info("wrote %s (%d bytes)", path.relative_to(ROOT), len(content))
    return True
