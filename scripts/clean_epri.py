"""Task 6: EPRI 'Powering Intelligence' (May 2024) Appendix A state table -> dw2_state_share.csv.

Columns: state, state_name, dc_mwh_2023, share_pct_2023, in_epri_table, page, source.
The table covers 44 states. States absent from it are kept with BLANK values
(in_epri_table = False) -- never zero, never estimated.
"""

from __future__ import annotations

import logging
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "data" / "raw" / "reports"
OUT = ROOT / "data" / "clean" / "dw2_state_share.csv"
URL = "https://restservice.epri.com/publicdownload/000000003002028905/0/Product"
APPENDIX_PAGES = (27, 28)  # 0-based indices; printed pages 28-29

NAMES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}
# Row: name, 2023 MWh, 2023 %EC, then 4 scenario (MWh, %) pairs.
ROW = re.compile(r"^([A-Z][A-Za-z .]+?) ([\d,]+) ([\d.]+)%((?: [\d,]+ [\d.]+%){4})$")

log = logging.getLogger("clean_epri")


def fail(msg: str) -> None:
    log.error(msg)
    sys.exit(1)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    files = sorted(PDF.glob("epri24_*.pdf"))
    if len(files) != 1:
        fail(f"expected one epri24 PDF, found {len(files)}")
    rows = []
    with pdfplumber.open(files[0]) as pdf:
        for i in APPENDIX_PAGES:
            for line in (pdf.pages[i].extract_text() or "").splitlines():
                m = ROW.match(line.strip())
                if m:
                    name = m.group(1)
                    if name not in NAMES:
                        fail(f"unknown state name {name!r} on page {i + 1}")
                    rows.append({"state": NAMES[name], "state_name": name,
                                 "dc_mwh_2023": int(m.group(2).replace(",", "")),
                                 "share_pct_2023": float(m.group(3)), "page": i + 1})
    df = pd.DataFrame(rows)
    if df["state"].duplicated().any():
        fail(f"duplicate states {df.loc[df.state.duplicated(), 'state'].tolist()}")
    log.info("parsed %d state rows from printed pages %s", len(df), [p + 1 for p in APPENDIX_PAGES])

    va = df[df.state == "VA"].iloc[0]
    if va.dc_mwh_2023 != 33_851_122 or va.share_pct_2023 != 25.59:
        fail(f"Virginia check failed: {va.dc_mwh_2023} MWh, {va.share_pct_2023}%")
    log.info("Virginia check ok: 33,851,122 MWh, 25.59%%")

    # Document has no stated 2023 national total. Consistency check against its own claim
    # "fifteen states account for 80% of the national data center load" (p.2, p.5, p.12).
    top15 = df.nlargest(15, "dc_mwh_2023")["dc_mwh_2023"].sum()
    log.info("sum of 44 states = %s MWh; top-15 = %s MWh = %.1f%% of the 44-state sum (report: ~80%% of national)",
             f"{df.dc_mwh_2023.sum():,}", f"{top15:,}", top15 / df.dc_mwh_2023.sum() * 100)

    full = pd.DataFrame({"state": list(NAMES.values()), "state_name": list(NAMES.keys())})
    out = full.merge(df.drop(columns="state_name"), on="state", how="left")
    out["in_epri_table"] = out["dc_mwh_2023"].notna()
    out["dc_mwh_2023"] = out["dc_mwh_2023"].astype("Int64")
    out["page"] = out["page"].astype("Int64")
    out["source"] = f"EPRI, Powering Intelligence (May 2024), Appendix A; {URL}"
    absent = out.loc[~out.in_epri_table, "state"].tolist()
    log.info("states not in EPRI table (left blank): %s", absent)
    if len(out) != 51:
        fail(f"{len(out)} rows")
    out.to_csv(OUT, index=False)
    log.info("wrote %s (51 rows, %d with values)", OUT.relative_to(ROOT), out.in_epri_table.sum())
    bins = pd.cut(out["share_pct_2023"], [0, 5, 10, 20, 100], right=False, labels=["<5", "5-10", "10-20", "20+"])
    log.info("DW2 bin counts: %s", bins.value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()
