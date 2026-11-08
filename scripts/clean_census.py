"""Task 2: Census C30 private construction SAAR -> data/clean/p2_construction.csv.

Columns: month (YYYY-MM), series (data_center | general_office), value_musd_saar, status (p/r/blank).
Acceptance: two series, no missing months from 2018-01, latest month matches the release PDF.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import openpyxl
import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "census"
OUT = ROOT / "data" / "clean" / "p2_construction.csv"
START = "2018-01"
SERIES = {"Data center": "data_center", "General": "general_office"}
MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
DATE_RE = re.compile(r"^([A-Z][a-z]{2})-(\d{2})([pr]?)$")

log = logging.getLogger("clean_census")


def fail(msg: str) -> None:
    log.error(msg)
    sys.exit(1)


def one(pattern: str) -> Path:
    files = sorted(RAW.glob(pattern))
    if len(files) != 1:
        fail(f"expected exactly one {pattern} in {RAW}, found {len(files)}")
    return files[0]


def read_xlsx(path: Path) -> tuple[pd.DataFrame, str]:
    ws = openpyxl.load_workbook(path, read_only=True)["Private SA"]
    rows = list(ws.iter_rows(values_only=True))
    hdr_i = next(i for i, r in enumerate(rows) if r and r[0] == "Date")
    hdr = rows[hdr_i]
    # 'General' appears right after 'Office' (Office > General); make sure we take that one.
    i_off = hdr.index("Office")
    if hdr[i_off + 1] != "General":
        fail("column after 'Office' is not 'General'; layout changed")
    cols = {"Data center": hdr.index("Data center"), "General": i_off + 1}
    recs = []
    for r in rows[hdr_i + 1:]:
        if not isinstance(r[0], str):
            continue
        m = DATE_RE.match(r[0].strip())
        if not m:
            continue
        mon, yy, flag = m.groups()
        year = (1900 if int(yy) >= 90 else 2000) + int(yy)  # table spans 1993..present
        month = f"{year}-{MONTHS[mon]:02d}"
        if month < START:  # Data center series starts 2014-01; earlier cells are blank
            continue
        for label, ci in cols.items():
            v = r[ci]
            if v is None or not isinstance(v, (int, float)):
                fail(f"non-numeric {label} value {v!r} at {r[0]}")
            recs.append({"month": month, "series": SERIES[label], "value_musd_saar": float(v),
                         "status": {"p": "preliminary", "r": "revised"}.get(flag, "")})
    vintage = next((r[0] for r in rows if isinstance(r[0], str) and r[0].startswith("Source: U.S. Census Bureau")), "")
    office_latest = None
    for r in rows[hdr_i + 1:]:
        if isinstance(r[0], str) and DATE_RE.match(r[0].strip()):
            office_latest = (r[0], r[i_off])
            break
    df = pd.DataFrame(recs)
    df.attrs["office_latest"] = office_latest
    return df, vintage


def pdf_check(path: Path) -> tuple[str, int]:
    """Return (release month text, private Office SAAR $M for the latest month) from the release PDF."""
    with pdfplumber.open(path) as pdf:
        p1 = pdf.pages[0].extract_text() or ""
        m = re.search(r"MONTHLY CONSTRUCTION SPENDING, ([A-Z]+ \d{4})", p1)
        if not m:
            fail("release month not found on PDF page 1")
        # Page 3 table: first 'Office' line = total, second = private, third = public.
        office = [l for l in (pdf.pages[2].extract_text() or "").splitlines() if l.startswith("Office ")]
    if len(office) < 2:
        fail("Office rows not found on PDF page 3")
    private_latest = int(office[1].split()[1].replace(",", ""))
    return m.group(1), private_latest


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    xlsx, pdf = one("census_c30_privsatime_*.xlsx"), one("census_c30_release_*.pdf")
    df, vintage = read_xlsx(xlsx)
    log.info("parsed %d rows (%s .. %s); vintage line: %s", len(df), df.month.min(), df.month.max(), vintage)

    df = df[df["month"] >= START].sort_values(["series", "month"]).reset_index(drop=True)
    if df.duplicated(["series", "month"]).any():
        fail("duplicate series-month")

    # Acceptance 1: two series, no missing months.
    latest = df["month"].max()
    expected = pd.period_range(START, latest, freq="M").strftime("%Y-%m")
    for s, g in df.groupby("series"):
        missing = sorted(set(expected) - set(g["month"]))
        if missing:
            fail(f"{s}: missing months {missing}")
    if df["series"].nunique() != 2:
        fail("expected 2 series")

    # Acceptance 2: latest month and value match the release PDF.
    rel_month, pdf_office = pdf_check(pdf)
    rel_period = pd.Period(pd.to_datetime(rel_month, format="%B %Y"), freq="M").strftime("%Y-%m")
    xl_label, xl_office = df.attrs["office_latest"]
    if rel_period != latest:
        fail(f"latest xlsx month {latest} != release month {rel_month}")
    if int(xl_office) != pdf_office:
        fail(f"private Office latest: xlsx {xl_office} != PDF {pdf_office}")
    log.info("release check ok: %s; private Office %s = %d in both xlsx and PDF", rel_month, xl_label, pdf_office)

    df["source"] = f"U.S. Census Bureau, Construction Spending (C30), private SAAR; {vintage.removeprefix('Source: U.S. Census Bureau, Construction Spending, ').split('.')[0]} release"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    log.info("wrote %s: %d rows, %d months x 2 series", OUT.relative_to(ROOT), len(df), len(expected))
    piv = df.pivot(index="month", columns="series", values="value_musd_saar")
    log.info("first/last rows:\n%s", pd.concat([piv.head(2), piv.tail(3)]).to_string())
    cross = piv[piv["data_center"] > piv["general_office"]]
    log.info("first month data_center > general_office: %s", cross.index.min() if len(cross) else "never")


if __name__ == "__main__":
    main()
