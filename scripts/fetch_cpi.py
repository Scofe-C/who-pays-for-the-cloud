"""Task 3 download: BLS CPI-U all items, U.S. city average, NSA (CUUR0000SA0), monthly.

Uses the keyless BLS public API v1. v1 returns monthly values only (no M13 annual
average) [Verified 2026-11-07]. Annual-average handling is a cleaning decision.
"""

from __future__ import annotations

import json

import requests

from fetch_common import GENERIC_UA, log, raw_path, setup_logging, write_once

URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
SERIES = "CUUR0000SA0"
START, END = "2018", "2025"


def main() -> None:
    setup_logging()
    r = requests.post(URL, json={"seriesid": [SERIES], "startyear": START, "endyear": END},
                      headers={"User-Agent": GENERIC_UA}, timeout=120)
    r.raise_for_status()
    j = r.json()
    if j.get("status") != "REQUEST_SUCCEEDED":
        raise SystemExit(f"BLS error: {j.get('status')} {j.get('message')}")
    log.info("BLS %s: %d observations", SERIES, len(j["Results"]["series"][0]["data"]))
    write_once(raw_path("bls", f"bls_{SERIES}_monthly", ".json"), json.dumps(j, indent=1).encode("utf-8"))


if __name__ == "__main__":
    main()
