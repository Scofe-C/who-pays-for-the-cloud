"""Task 3 download: EIA API v2 electricity/retail-sales, annual, sectors ALL + RES, all state ids.

Route and facet names confirmed against the API metadata on 2026-11-07:
facets stateid, sectorid; data fields sales (million kWh), price (cents/kWh).
"""

from __future__ import annotations

import json

import requests

from fetch_common import GENERIC_UA, env, log, raw_path, setup_logging, write_once

URL = "https://api.eia.gov/v2/electricity/retail-sales/data/"
START, END = "2019", "2025"  # 2025 kept in raw; cleaning decides whether to use it
PAGE = 5000


def main() -> None:
    setup_logging()
    key = env("EIA_API_KEY")
    rows: list[dict] = []
    offset, total = 0, None
    while total is None or offset < total:
        params = {
            "api_key": key, "frequency": "annual", "data[]": ["sales", "price"],
            "facets[sectorid][]": ["ALL", "RES"], "start": START, "end": END,
            "sort[0][column]": "period", "sort[0][direction]": "asc",
            "offset": offset, "length": PAGE,
        }
        r = requests.get(URL, params=params, headers={"User-Agent": GENERIC_UA}, timeout=120)
        r.raise_for_status()
        resp = r.json()["response"]
        total = int(resp["total"])
        rows.extend(resp["data"])
        offset += PAGE
    if len(rows) != total:
        raise SystemExit(f"EIA row mismatch: got {len(rows)}, total {total}")
    out = {
        "source": URL, "params": {"frequency": "annual", "data": ["sales", "price"],
                                  "sectorid": ["ALL", "RES"], "start": START, "end": END},
        "total": total, "data": rows,
    }
    log.info("EIA rows: %d", total)
    write_once(raw_path("eia", "eia_retail_sales_annual", ".json"),
               json.dumps(out, indent=1).encode("utf-8"), secrets=(key,))


if __name__ == "__main__":
    main()
