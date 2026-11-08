"""Task 7: draft data/manual/facts.csv from report documents in data/raw/reports/ (scripted downloads)
and data/raw/energy_report/ (manual downloads, original filenames, read in place).

For each checklist id: search ONLY the document listed for that id, with a context-anchored
regex whose value group is a generic number (so a document value that differs from `expected`
is captured and flagged, not forced). Not found -> row left out and reported as missing.
`verified_by` is always left empty -- that column is the human's.

page = PDF page number as shown by a PDF viewer (1-based); source_url gets '#page=N'.
Run report -> notes/facts_run_report.md
"""

from __future__ import annotations

import csv
import datetime
import html
import logging
import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "data" / "raw" / "reports"
OUT = ROOT / "data" / "manual" / "facts.csv"
REPORT = ROOT / "notes" / "facts_run_report.md"
NUM = r"[\d][\d,]*(?:\.\d+)?"

SOURCES = {  # prefix: (title, url) -- DATA_SOURCES.md §C
    "lbnl24": ("LBNL 2024 United States Data Center Energy Usage Report",
               "https://eta-publications.lbl.gov/sites/default/files/2024-12/lbnl-2024-united-states-data-center-energy-usage-report_1.pdf"),
    "lbnl25": ("LBNL, United States Data Center Energy Usage Report: 2025 Update",
               "https://escholarship.org/content/qt33m6w3x0/qt33m6w3x0.pdf"),
    "epri24": ("EPRI, Powering Intelligence (May 2024)",
               "https://restservice.epri.com/publicdownload/000000003002028905/0/Product"),
    "epri26": ("EPRI 3002034696, Powering Intelligence 2026: Updated Scenarios of U.S. Data Center Electricity Use "
               "and Power Strategies", "https://powering-intelligence.epri.com/"),
    "iea25": ("IEA, Energy and AI (2025), full report PDF", "https://www.iea.org/reports/energy-and-ai/executive-summary"),
    "iea26": ("IEA, Key Questions on Energy and AI (2026), full report PDF",
              "https://www.iea.org/reports/key-questions-on-energy-and-ai/executive-summary"),
    "pjm": ("PJM 2028/2029 Base Residual Auction Report",
            "https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2028-2029/2028-2029-bra-results-report.pdf"),
    "ieefa": ("IEEFA, Projected data center growth spurs PJM capacity prices by factor of 10 (July 30, 2025)",
              "https://ieefa.org/resources/projected-data-center-growth-spurs-pjm-capacity-prices-factor-10"),
    "imm": ("Monitoring Analytics (IMM), Market Monitor Report, July 28, 2026",
            "https://www.monitoringanalytics.com/reports/Presentations/2026/IMM_MC_Market_Monitor_Report_20260728.pdf"),
    "jlarc": ("JLARC Report 598, Data Centers in Virginia", "https://jlarc.virginia.gov/pdfs/reports/Rpt598-2.pdf"),
    "vatax": ("Virginia Dept. of Taxation, Biennial Data Center Retail Sales and Use Tax Exemption Report (RD40, Jan 2, 2026)",
              "https://rga.lis.virginia.gov/Published/2026/RD40/PDF"),
    "vabudget": ("Williams Mullen, Virginia budget creates new electricity consumption tax for data centers (secondary; HB 30)",
                 "https://www.williamsmullen.com/insights/news/legal-news/virginia-budget-creates-new-electricity-consumption-tax-data-centers"),
    "mdopc": ("Maryland Office of People's Counsel, press release July 24, 2025",
              "https://content.govdelivery.com/accounts/MDOPC/bulletins/3ead2f8"),
    "peco": ("PhillyVoice, PECO bill increase (secondary)", "https://www.phillyvoice.com/peco-bill-increase-supply-costs/"),
    "dcw": ("Data Center Watch report", "https://www.datacenterwatch.org/report"),
}
# Sources the scripts could not fetch (HTTP 403 / JavaScript app); the human downloaded them by hand
# into data/raw/energy_report/ with their original filenames. Read in place, never renamed.
MANUAL_DIR = ROOT / "data" / "raw" / "energy_report"
MANUAL = {
    "lbnl25": "qt33m6w3x0.pdf",
    "epri26": "3002034696_Powering Intelligence 2026_ Updated Scenarios of U.S. Data Center Electricity Use "
              "and Power Strategies.PDF",
    "iea25": "EnergyandAI.pdf",
    "iea26": "KeyQuestionsonEnergyandAI.pdf",
}

# id, expected, unit, metric, period, pattern (group v = value; optional group neg = minus sign), notes
F = [
    # LBNL 2024
    ("lbnl24_2014_twh", "58", "TWh", "U.S. data center electricity use", "2014",
     rf"remained stable between 2014– ?2016 at about (?P<v>{NUM}) TWh", "report gives 2014-2016 'about' value"),
    ("lbnl24_2023_twh", "176", "TWh", "U.S. data center electricity use", "2023", rf"reaching (?P<v>{NUM}) TWh by 2023", ""),
    ("lbnl24_2023_share", "4.4", "% of U.S. electricity", "Data center share of U.S. electricity consumption", "2023",
     rf"reaching {NUM} TWh by 2023, representing (?P<v>{NUM})% of total", ""),
    ("lbnl24_2028_low", "6.7", "% of U.S. electricity", "Projected data center share, low end", "2028 (report year 2024)",
     rf"represents (?P<v>{NUM})% to {NUM}% of total U\.S\. electricity consumption forecasted for 2028", ""),
    ("lbnl24_2028_high", "12", "% of U.S. electricity", "Projected data center share, high end", "2028 (report year 2024)",
     rf"represents {NUM}% to (?P<v>{NUM})% of total U\.S\. electricity consumption forecasted for 2028", ""),
    # LBNL 2025 (manual download)
    ("lbnl25_2024_twh", "192", "TWh", "U.S. data center electricity use", "2024",
     rf"estimate of data center electricity use in 2024 is (?P<v>{NUM}) terawatt-hours", ""),
    ("lbnl25_2024_share", "4.7", "% of U.S. electricity", "Data center share of U.S. electricity consumption", "2024",
     rf"in 2024 is {NUM} terawatt-hours \(TWh\), accounting for (?P<v>{NUM})% of total", ""),
    ("lbnl25_2030_mid", "11.8", "% of U.S. electricity", "Projected data center share, Reference Case",
     "2030 (report year 2025)", rf"could account for (?P<v>{NUM})% of total U\.S\. electricity by 2030", ""),
    ("lbnl25_2030_low", "9.5", "% of U.S. electricity", "Projected data center share, Compounded Uncertainty low",
     "2030 (report year 2025)", rf"Compounded Uncertainty Range of {NUM}[–-]{NUM} TWh, equal to (?P<v>{NUM})[–-]{NUM}%", ""),
    ("lbnl25_2030_high", "15.3", "% of U.S. electricity", "Projected data center share, Compounded Uncertainty high",
     "2030 (report year 2025)", rf"Compounded Uncertainty Range of {NUM}[–-]{NUM} TWh, equal to {NUM}[–-](?P<v>{NUM})%", ""),
    ("lbnl25_2030_twh_low", "521", "TWh", "Projected data center electricity use, Compounded Uncertainty low",
     "2030 (report year 2025)", rf"Compounded Uncertainty Range of (?P<v>{NUM})[–-]{NUM} TWh", ""),
    ("lbnl25_2030_twh_high", "843", "TWh", "Projected data center electricity use, Compounded Uncertainty high",
     "2030 (report year 2025)", rf"Compounded Uncertainty Range of {NUM}[–-](?P<v>{NUM}) TWh", ""),
    # EPRI 2024
    ("epri24_2030_low", "4.6", "% of U.S. electricity generation", "Projected data center share, low-growth scenario",
     "2030 (report year 2024)", rf"Data centers grow to consume (?P<v>{NUM})% to {NUM}% of U\.S\. electricity generation annually by 2030", ""),
    ("epri24_2030_high", "9.1", "% of U.S. electricity generation", "Projected data center share, higher-growth scenario",
     "2030 (report year 2024)", rf"Data centers grow to consume {NUM}% to (?P<v>{NUM})% of U\.S\. electricity generation annually by 2030", ""),
    ("epri24_15states_share", "80", "% of national data center load", "Share of data center load in top 15 states", "2023",
     rf"fifteen states account for (?P<v>{NUM})% of the national data center load", ""),
    ("epri24_va_mwh", "33851122", "MWh", "Virginia data center electricity consumption", "2023",
     rf"Virginia (?P<v>{NUM}) {NUM}% {NUM} {NUM}%", "Table 2"),
    ("epri24_va_share", "25.59", "% of state electricity", "Virginia data center share of state electricity", "2023",
     rf"Virginia {NUM} (?P<v>{NUM})% {NUM} {NUM}%", "Table 2"),
    # EPRI 2026 (manual download)
    ("epri26_2030_low", "9", "% of U.S. electricity demand", "Projected data center share, low end of scenarios",
     "2030 (report year 2026)", rf"total electricity demand in 2030 ranges from (?P<v>{NUM})% to {NUM}%", ""),
    ("epri26_2030_high", "17", "% of U.S. electricity demand", "Projected data center share, high end of scenarios",
     "2030 (report year 2026)", rf"total electricity demand in 2030 ranges from {NUM}% to (?P<v>{NUM})%", ""),
    ("epri26_va_2030_low", "39", "% of state electricity", "Virginia projected data center share, low end",
     "2030 (report year 2026)", rf"Virginia implies a share increasing to between (?P<v>{NUM})% and {NUM}% by 2030", ""),
    ("epri26_va_2030_high", "57", "% of state electricity", "Virginia projected data center share, high end",
     "2030 (report year 2026)", rf"Virginia implies a share increasing to between {NUM}% and (?P<v>{NUM})% by 2030", ""),
    # IEA (manual download of the full report PDFs)
    ("iea25_2024_twh", "415", "TWh", "Global data center electricity consumption", "2024",
     rf"electricity consumption in 2024, or (?P<v>{NUM}) terawatt-hours", ""),
    ("iea25_us_share_2024", "45", "% of global", "U.S. share of global data center electricity", "2024",
     rf"The United States accounted for the largest share of global data centre electricity consumption in 2024 \((?P<v>{NUM})%\)", ""),
    ("iea26_2023_twh", "360", "TWh", "Global data center electricity consumption", "2023",
     rf"Total electricity consumption \(TWh\) World (?P<v>{NUM}) {NUM} {NUM} {NUM}",
     "Annex Table A.4, Base Case; same table gives 416 for 2024 (IEA 2025 text: 415)"),
    ("iea26_2025_twh", "485","TWh", "Global data center electricity consumption", "2025",
     rf"roughly doubling from (?P<v>{NUM}) TWh in 2025 to {NUM} TWh in 2030", ""),
    ("iea26_2030_twh", "950", "TWh", "Projected global data center electricity, Base Case", "2030 (report year 2026)",
     rf"roughly doubling from {NUM} TWh in 2025 to (?P<v>{NUM}) TWh in 2030",
     "rounded text value; Annex Table A.4 Base Case shows 945 for 2030"),
    ("iea26_2025_growth", "17", "%", "Growth in global data center electricity", "2025",
     rf"grew by (?P<v>{NUM})% in 2025, in line with IEA projections", ""),
    # PJM BRA report, p8 history table (row = delivery year, clearing price, cleared UCAP MW ...)
    ("pjm_2425", "28.92", "USD/MW-day", "PJM RTO capacity clearing price", "2024/25", rf"2024/25\d? \$(?P<v>{NUM}) {NUM} {NUM}%", "BRA history table"),
    ("pjm_2526", "269.92", "USD/MW-day", "PJM RTO capacity clearing price", "2025/26", rf"2025/26\d? \$(?P<v>{NUM}) {NUM} {NUM}%", "BRA history table"),
    ("pjm_2627", "329.17", "USD/MW-day", "PJM RTO capacity clearing price", "2026/27", rf"2026/27\d? \$(?P<v>{NUM}) {NUM} {NUM}%", "BRA history table"),
    ("pjm_2728", "333.44", "USD/MW-day", "PJM RTO capacity clearing price", "2027/28", rf"2027/28\d? \$(?P<v>{NUM}) {NUM} {NUM}%", "cleared at the price cap"),
    ("pjm_2829", "325.00", "USD/MW-day", "PJM RTO capacity clearing price", "2028/29", rf"2028/29\d? \$(?P<v>{NUM}) {NUM} {NUM}%", "cleared at the price cap"),
    ("pjm_2829_uncapped", "554.72", "USD/MW-day", "Simulated clearing price with no cap and floor", "2028/29",
     rf"For the 2028/2029 simulated BRA, all prices cleared at \$(?P<v>{NUM})", "simulation; COMED LDA differs"),
    ("pjm_2829_shortfall", "6831", "MW UCAP", "Procured capacity below RTO Reliability Requirement", "2028/29",
     rf"or (?P<v>{NUM}) MW UCAP below the RTO Reliability Requirement", ""),
    # IMM
    ("imm_4auction_dc", "29.4", "USD billion", "Capacity market charges resulting from data center load, last four auctions",
     "four BRAs through 2028/29", rf"over the last four capacity market auctions equal \$(?P<v>{NUM})B", ""),
    ("imm_4auction_total", "63.6", "USD billion", "Total capacity market charges, last four auctions", "four BRAs through 2028/29",
     rf"total capacity market charges over (?:those|the last) four (?:capacity market )?auctions (?:equal|were|of) \$(?P<v>{NUM})B", ""),
    ("imm_4auction_share", "46.2", "%", "Data center share of capacity market charges, last four auctions", "four BRAs through 2028/29",
     rf"equal \${NUM}B, or (?P<v>{NUM}) percent of total capacity market charges over those four auctions", ""),
    ("imm_2829_dc", "6.3", "USD billion", "Capacity market charges resulting from data center load", "2028/29",
     rf"of the \${NUM}B in capacity market charges, \$(?P<v>{NUM})B was a result of data center load", ""),
    ("imm_2829_total", "16.4", "USD billion", "Total capacity market charges", "2028/29",
     rf"of the \$(?P<v>{NUM})B in capacity market charges, \${NUM}B was a result of data center load", ""),
    ("imm_2829_share", "38.2", "%", "Data center share of capacity market charges", "2028/29",
     rf"\${NUM}B was a result of data center load ?\. This was (?P<v>{NUM}) percent", "IMM's published share"),
    # JLARC
    ("jlarc_jobs_total", "74000", "jobs per year", "Jobs supported by data center industry incl. indirect + induced", "annual average",
     rf"provides approximately (?P<v>{NUM}) jobs", ""),
    ("jlarc_jobs_construction", "59000", "jobs per year", "Jobs during construction phase incl. indirect + induced", "annual average",
     rf"contribute (?P<v>{NUM}) jobs annually during the construc", ""),
    ("jlarc_jobs_operations", "not in checklist", "jobs per year", "Jobs during operations phase incl. indirect + induced",
     "annual average", rf"Total impact {NUM} jobs (?P<v>{NUM}) jobs {NUM} jobs", "extra row for F3 waffle; table on economic impacts"),
    ("jlarc_fy23_exemption", "928.6", "USD million", "Sales tax saved via data center exemption (self-reported, state+local+regional)",
     "FY2023", rf"reported saving \$(?P<v>{NUM}) million in sales taxes", "self-reported"),
    ("jlarc_return_per_dollar", "0.48", "cents of state revenue per USD 1 exempted", "Return in state revenue per $1 spent on the exemption",
     "annual average", rf"Return in revenue per \$1 spent (?P<v>{NUM})¢", "printed as 48¢ (= USD 0.48); Table 2-2"),
    # Virginia Tax RD40 (p.3 table text is garbled by extraction; p.4 Table 2 is clean)
    ("vatax_fy24", "1292457000", "USD", "DCRSUT benefit reported by data center operators", "FY2024",
     rf"DCRSUT benefit reported (?P<v>{NUM}) {NUM} {NUM} Total data center investment", "self-reported; Table 2"),
    ("vatax_fy25", "1941390000", "USD", "DCRSUT benefit reported by data center operators", "FY2025",
     rf"DCRSUT benefit reported {NUM} (?P<v>{NUM}) {NUM} Total data center investment", "self-reported; Table 2"),
    # Virginia budget (secondary)
    ("vabudget_rate", "0.011", "USD per kWh", "New data center electricity consumption tax rate", "from July 1, 2026",
     rf"electricity consumption tax of \$(?P<v>{NUM}) per kWh", "secondary source; primary HB 30 text not fetched"),
    ("vabudget_cap", "600", "USD million per year", "Annual revenue cap (collections above are refunded)", "FY2027 onward",
     rf"collections exceed \$(?P<v>{NUM}) million", "secondary source"),
    # IEEFA
    ("ieefa_wmd", "18", "USD per month", "Capacity-price effect on average residential bill, western Maryland", "2025/26",
     rf"average residential bill by \$(?P<v>{NUM})/month in western Maryland", ""),
    ("ieefa_oh", "16", "USD per month", "Capacity-price effect on average residential bill, Ohio", "2025/26",
     rf"by about \$(?P<v>{NUM})/month in Ohio", ""),
    ("ieefa_dc_capacity", "10", "USD per month", "Part of Pepco D.C. bill increase due to capacity prices (DC OPC estimate)",
     "from June 2025", rf"estimates that \$(?P<v>{NUM})/month, or about half of this increase", "dc = Washington D.C., not data centers"),
    ("ieefa_dc_total", "21", "USD per month", "Average Pepco D.C. residential bill increase", "from June 2025",
     rf"Pepco residential customers saw their bills go up by an average of \$(?P<v>{NUM})/month", "dc = Washington D.C."),
    # Maryland OPC table: cumulative (vs 2024/25) | most recent auction (vs 2025/26) | net after RMR credits
    ("mdopc_bge_cumulative", "16.49", "USD per month", "BGE residential bill increase, cumulative last two auctions",
     "2026/27 vs 2024/25", rf"Baltimore Gas and Electric After credits \(see explanation below\) \$(?P<v>{NUM}) \${NUM}", ""),
    ("mdopc_bge_latest", "0.83", "USD per month", "BGE residential bill increase, most recent auction",
     "2026/27 vs 2025/26", rf"Baltimore Gas and Electric After credits \(see explanation below\) \${NUM} \$(?P<v>{NUM})", ""),
    ("mdopc_bge_net", "-3.36", "USD per month", "BGE net bill change after RMR credits", "2026/27",
     rf"Baltimore Gas and Electric After credits \(see explanation below\) \${NUM} \${NUM} \((?P<neg>-)\$(?P<v>{NUM})\)", "decrease"),
    ("mdopc_pepco_net", "2.50", "USD per month", "Pepco (MD) net bill change after RMR credits", "2026/27",
     rf"Pepco \(Maryland\) and SMECO After credits \(see explanation below\) \${NUM} \${NUM} \$(?P<v>{NUM})", ""),
    # PECO (secondary)
    ("peco_2026_usd", "4.94", "USD per month", "Typical PECO residential bill increase (700 kWh)", "from June 2026",
     rf"will increase by \$(?P<v>{NUM}) per month — a {NUM}% increase", "secondary source; PECO primary not fetched"),
    ("peco_2026_pct", "3.1", "%", "Typical PECO residential bill increase", "from June 2026",
     rf"will increase by \${NUM} per month — a (?P<v>{NUM})% increase", "secondary source"),
    # Data Center Watch
    ("dcw_blocked_delayed", "64", "USD billion", "Data center projects blocked or delayed by local opposition", "2023 to Q1 2025 report",
     rf"TL;DR: \$(?P<v>{NUM}) billion in U\.S\. data center projects have been blocked or delayed", ""),
]

log = logging.getLogger("draft_facts")


def is_manual(prefix: str) -> bool:
    return prefix in MANUAL and (MANUAL_DIR / MANUAL[prefix]).exists()


def load_pages(prefix: str) -> tuple[list[str], str, str] | None:
    files = sorted(REPORTS.glob(f"{prefix}_*"))
    if is_manual(prefix):  # manual full document beats a scripted stub (e.g. epri26 JS shell)
        f = MANUAL_DIR / MANUAL[prefix]
        # Original filename has no date; use the file's modification date (= manual download date).
        as_of = datetime.date.fromtimestamp(f.stat().st_mtime).isoformat()
    elif files:
        f = files[-1]
        as_of = f.stem.rsplit("_", 1)[-1]
    else:
        return None
    if f.suffix.lower() == ".pdf":
        with pdfplumber.open(f) as pdf:
            pages = [re.sub(r"\s+", " ", p.extract_text() or "") for p in pdf.pages]
        return pages, as_of, "pdf"
    t = f.read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"(?s)<(script|style|noscript)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
    return [t], as_of, "html"


def evidence(text: str, start: int, end: int, max_words: int = 25) -> str:
    match = text[start:end].split()
    room = max(0, max_words - len(match))
    before = text[:start].split()[-(room // 2):] if room // 2 else []
    after = text[end:].split()[: room - len(before)]
    return " ".join(before + match + after)[:400]


def num(s: str) -> float:
    return float(s.replace(",", ""))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    docs = {p: load_pages(p) for p in SOURCES}
    rows, missing, mismatch = [], [], []
    for fid, expected, unit, metric, period, pat, note in F:
        prefix = fid.split("_", 1)[0]
        doc = docs.get(prefix)
        if pat is None or doc is None or (doc[2] == "html" and len(doc[0][0]) < 500):
            why = "source not downloaded (HTTP 403)" if doc is None else \
                  "source page has no text (JavaScript app)" if pat is not None or len(doc[0][0]) < 500 else "no pattern"
            missing.append((fid, why))
            continue
        pages, as_of, kind = doc
        hit = None
        for i, t in enumerate(pages):
            m = re.search(pat, t)
            if m:
                hit = (i + 1, t, m)
                break
        if not hit:
            missing.append((fid, "not found in document"))
            continue
        pg, t, m = hit
        v = m.group("v").replace(",", "")
        if "neg" in m.groupdict() and m.group("neg"):
            v = "-" + v
        title, url = SOURCES[prefix]
        url_is_pdf = kind == "pdf" and prefix not in ("iea25", "iea26", "epri26")  # these URLs are landing pages
        if is_manual(prefix):
            note = (note + "; " if note else "") + f"page = PDF page of data/raw/energy_report/{MANUAL[prefix]}"
        row = {
            "id": fid, "value": v, "unit": unit, "metric": metric, "period": period,
            "source_title": title, "source_url": f"{url}#page={pg}" if url_is_pdf else url,
            "page": str(pg) if kind == "pdf" else "web",
            "evidence": evidence(t, m.start(), m.end()), "as_of": as_of, "expected": expected,
            "verified_by": "", "notes": note or "none",
        }
        try:
            if num(expected) != num(v):
                mismatch.append((fid, v, expected))
                row["notes"] = (note + "; " if note else "") + f"FLAG: document value {v} != expected {expected}"
        except ValueError:
            pass  # expected is not numeric (extra row)
        rows.append(row)

    # Keep the human's verification when a row's value is unchanged; a changed value needs re-verification.
    if OUT.exists():
        old = {r["id"]: r for r in csv.DictReader(OUT.read_text(encoding="utf-8").splitlines())}
        kept = 0
        for row in rows:
            o = old.get(row["id"])
            if o and o["verified_by"].strip():
                if o["value"] == row["value"]:
                    row["verified_by"] = o["verified_by"]
                    kept += 1
                else:
                    log.warning("%s: value changed %s -> %s; verified_by cleared", row["id"], o["value"], row["value"])
        # Hand-entered rows (ids with no checklist pattern, e.g. web pages that block automated fetches)
        # are carried over unchanged instead of being dropped.
        drafted = {fid for fid, *_ in F}
        hand = [o for i, o in old.items() if i not in drafted]
        for o in hand:
            log.info("%s: hand-entered row kept as is", o["id"])
        rows += hand
        log.info("verified_by kept for %d rows; %d rows need verification", kept, sum(not r["verified_by"] for r in rows))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    cols =["id", "value", "unit", "metric", "period", "source_title", "source_url", "page", "evidence",
            "as_of", "expected", "verified_by", "notes"]
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)

    lines = ["# facts.csv run report", "", f"Generated by `scripts/draft_facts.py`. Rows found: **{len(rows)}**, "
             f"missing: **{len(missing)}**, value != expected: **{len(mismatch)}**.", "",
             "## Missing (left out, never filled from elsewhere)", "", "| id | reason |", "|---|---|"]
    lines += [f"| {i} | {r} |" for i, r in missing]
    lines += ["", "## Value differs from expected", "", "| id | document value | expected |", "|---|---|---|"]
    lines += [f"| {i} | {v} | {e} |" for i, v, e in mismatch]
    lines += ["", "## Human verification", "", "Open each `source_url` (PDF links jump to `page`), find `evidence`, "
              "check `value`, write initials in `verified_by`. `page` is the PDF viewer page, not the printed page number."]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("rows found %d, missing %d, mismatch %d -> %s, %s", len(rows), len(missing), len(mismatch),
             OUT.relative_to(ROOT), REPORT.relative_to(ROOT))
    for i, r in missing:
        log.info("missing %s: %s", i, r)
    for i, v, e in mismatch:
        log.info("mismatch %s: doc %s vs expected %s", i, v, e)


if __name__ == "__main__":
    main()
