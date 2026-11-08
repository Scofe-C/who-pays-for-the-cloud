"""Fail (exit 1) if any value from .env appears in a tracked or staged file.

Run before every commit:  python scripts/check_secrets.py
Never prints the secret itself, only the key name and file path.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIN_LEN = 8  # ignore trivially short values that would false-positive

log = logging.getLogger("check_secrets")


def load_env(path: Path) -> dict[str, str]:
    if not path.exists():
        log.error(".env not found at %s", path)
        sys.exit(2)
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        if len(v) >= MIN_LEN:
            out[k.strip()] = v
    return out


def candidate_files() -> list[Path]:
    """Tracked + staged + untracked-but-not-ignored files (what a commit could include)."""
    res = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT, capture_output=True, check=True,
    )
    return [ROOT / p for p in res.stdout.decode("utf-8").split("\0") if p]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    secrets = load_env(ROOT / ".env")
    hits = 0
    files = candidate_files()
    for f in files:
        if f.name == ".env" or not f.is_file():
            continue
        data = f.read_bytes()
        for key, val in secrets.items():
            if val.encode("utf-8") in data:
                log.error("secret %s found in %s", key, f.relative_to(ROOT))
                hits += 1
    if hits:
        log.error("%d secret hit(s). Do not commit.", hits)
        return 1
    log.info("ok: %d files scanned, %d secret values checked", len(files), len(secrets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
