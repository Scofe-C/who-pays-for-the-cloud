"""Task 2 download: Census C30 private construction spending (SAAR) + current release PDF."""

from __future__ import annotations

import requests

from fetch_common import GENERIC_UA, log, raw_path, setup_logging, write_once

FILES = {
    "census_c30_privsatime": ("https://www.census.gov/construction/c30/xlsx/privsatime.xlsx", ".xlsx"),
    "census_c30_release": ("https://www.census.gov/construction/c30/pdf/release.pdf", ".pdf"),
}


def main() -> None:
    setup_logging()
    for stem, (url, suffix) in FILES.items():
        r = requests.get(url, headers={"User-Agent": GENERIC_UA}, timeout=120)
        r.raise_for_status()
        log.info("GET %s -> %d, Last-Modified=%s", url, r.status_code, r.headers.get("Last-Modified"))
        write_once(raw_path("census", stem, suffix), r.content)


if __name__ == "__main__":
    main()
