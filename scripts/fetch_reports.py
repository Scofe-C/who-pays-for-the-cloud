"""Task 6/7 download: report documents from DATA_SOURCES.md §C into data/raw/reports/.

Write-once, dated filenames. A failed download is reported, never replaced by another source.
"""

from __future__ import annotations

import logging

import requests

from fetch_common import GENERIC_UA, log, raw_path, setup_logging, write_once, RAW

SOURCES = {  # prefix: URL (DATA_SOURCES.md §C, verbatim)
    "lbnl24": "https://eta-publications.lbl.gov/sites/default/files/2024-12/lbnl-2024-united-states-data-center-energy-usage-report_1.pdf",
    "lbnl25": "https://escholarship.org/content/qt33m6w3x0/qt33m6w3x0.pdf",
    "epri24": "https://restservice.epri.com/publicdownload/000000003002028905/0/Product",
    "epri26": "https://powering-intelligence.epri.com/",
    "iea25": "https://www.iea.org/reports/energy-and-ai/executive-summary",
    "iea26": "https://www.iea.org/reports/key-questions-on-energy-and-ai/executive-summary",
    "pjm": "https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2028-2029/2028-2029-bra-results-report.pdf",
    "pjm2627": "https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2026-2027/2026-2027-bra-report.pdf",  # H1 cap check
    "ieefa": "https://ieefa.org/resources/projected-data-center-growth-spurs-pjm-capacity-prices-factor-10",
    "imm": "https://www.monitoringanalytics.com/reports/Presentations/2026/IMM_MC_Market_Monitor_Report_20260728.pdf",
    "jlarc": "https://jlarc.virginia.gov/pdfs/reports/Rpt598-2.pdf",
    "vatax": "https://rga.lis.virginia.gov/Published/2026/RD40/PDF",
    "vabudget": "https://www.williamsmullen.com/insights/news/legal-news/virginia-budget-creates-new-electricity-consumption-tax-data-centers",
    "mdopc": "https://content.govdelivery.com/accounts/MDOPC/bulletins/3ead2f8",
    "peco": "https://www.phillyvoice.com/peco-bill-increase-supply-costs/",
    "dcw": "https://www.datacenterwatch.org/report",
    "scc": "https://www.scc.virginia.gov/about-the-scc/newsreleases/release/scc-issues-order-on-dev-biennial-review-2025/scc-rules-in-dev-biennial-review-case.html",
}
# Honest generic client only. Sites that block it are left for the human to download manually.


def suffix_for(r: requests.Response) -> str:
    ct = r.headers.get("Content-Type", "").lower()
    if "pdf" in ct or r.content[:5] == b"%PDF-":
        return ".pdf"
    return ".html"


def main() -> None:
    setup_logging()
    d = RAW / "reports"
    failed = {}
    for prefix, url in SOURCES.items():
        if list(d.glob(f"{prefix}_*")):
            log.info("%s: already downloaded", prefix)
            continue
        r = None
        for ua in (GENERIC_UA,):
            try:
                r = requests.get(url, headers={"User-Agent": ua}, timeout=120)
            except requests.RequestException as e:
                failed[prefix] = repr(e)
                r = None
                continue
            if r.status_code == 200 and len(r.content) > 2000:
                break
        if r is None or r.status_code != 200:
            failed[prefix] = f"HTTP {getattr(r, 'status_code', 'n/a')}"
            continue
        failed.pop(prefix, None)
        log.info("%s: %d %s %d bytes", prefix, r.status_code, r.headers.get("Content-Type"), len(r.content))
        write_once(raw_path("reports", prefix, suffix_for(r)), r.content)
    for p, why in failed.items():
        log.warning("FAILED %s: %s (%s)", p, why, SOURCES[p])


if __name__ == "__main__":
    main()
