"""Task 4 download: SEC EDGAR company_tickers.json + companyfacts for 5 companies.

User-Agent from .env SEC_USER_AGENT (SEC requirement). Rate limit: <= 10 req/s; we sleep 0.25 s.
CIKs are resolved from company_tickers.json by ticker, not hard-coded.
"""

from __future__ import annotations

import json
import time

import requests

from fetch_common import env, log, raw_path, setup_logging, write_once

TICKERS = {"MSFT": "Microsoft", "GOOGL": "Alphabet", "AMZN": "Amazon", "META": "Meta", "ORCL": "Oracle"}
EXPECTED_CIK = {"MSFT": 789019, "GOOGL": 1652044, "AMZN": 1018724, "META": 1326801, "ORCL": 1341439}
DELAY_S = 0.25


def main() -> None:
    setup_logging()
    s = requests.Session()
    s.headers.update({"User-Agent": env("SEC_USER_AGENT"), "Accept-Encoding": "gzip, deflate"})

    r = s.get("https://www.sec.gov/files/company_tickers.json", timeout=120)
    r.raise_for_status()
    write_once(raw_path("sec", "sec_company_tickers", ".json"), r.content)
    by_ticker = {v["ticker"]: int(v["cik_str"]) for v in r.json().values()}

    for t, name in TICKERS.items():
        cik = by_ticker.get(t)
        if cik is None:
            raise SystemExit(f"ticker {t} not in company_tickers.json")
        flag = "matches" if cik == EXPECTED_CIK[t] else f"DIFFERS from expected {EXPECTED_CIK[t]}"
        log.info("%s (%s): CIK %d %s", name, t, cik, flag)
        time.sleep(DELAY_S)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        r = s.get(url, timeout=120)
        r.raise_for_status()
        entity = r.json().get("entityName")
        log.info("GET %s -> %d, entityName=%s", url, r.status_code, entity)
        write_once(raw_path("sec", f"sec_companyfacts_{t}_CIK{cik:010d}", ".json"), r.content)


if __name__ == "__main__":
    main()
