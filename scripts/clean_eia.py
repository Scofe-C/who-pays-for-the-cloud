"""Task 3: EIA retail sales/price + BLS CPI-U -> p1_state_price_growth.csv (all sectors)
and p1_state_price_growth_residential.csv.

Real prices in 2024 dollars:
  CPI_y            = mean of the 12 monthly CUUR0000SA0 values in year y
  price_real_2019  = price_nominal_2019 * CPI_2024 / CPI_2019
  price_real_2024  = price_nominal_2024
  price_change_pct = (price_real_2024 / price_real_2019 - 1) * 100
  sales_change_pct = (sales_2024 / sales_2019 - 1) * 100
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "clean"
Y0, Y1 = 2019, 2024
MKWH_TO_MWH = 1000  # million kWh -> MWh

STATES_51 = (
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV "
    "NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY"
).split()

# PJM membership (14 jurisdictions) [Verified: pjm.com/about-pjm/who-we-are/territory-served,
# 2026-11-07: "all or parts of DE, IL, IN, KY, MD, MI, NJ, NC, OH, PA, TN, VA, WV and DC"].
# full vs partial split [Assumption: carried from DATA_PIPELINE.md; pjm.com does not state it.
# Human must confirm before P1 colours by this column].
PJM_FULL = {"DE", "MD", "NJ", "OH", "PA", "VA", "WV", "DC"}
PJM_PARTIAL = {"IL", "IN", "KY", "MI", "NC", "TN"}

SECTORS = {"ALL": "p1_state_price_growth.csv", "RES": "p1_state_price_growth_residential.csv"}

log = logging.getLogger("clean_eia")


def fail(msg: str) -> None:
    log.error(msg)
    sys.exit(1)


def one(pattern: str) -> Path:
    files = sorted(RAW.glob(pattern))
    if len(files) != 1:
        fail(f"expected exactly one {pattern}, found {len(files)}")
    return files[0]


def cpi_annual() -> dict[int, float]:
    data = json.loads(one("bls/bls_CUUR0000SA0_monthly_*.json").read_text())["Results"]["series"][0]["data"]
    out = {}
    for y in (Y0, Y1):
        months = [d for d in data if d["year"] == str(y) and d["period"] in {f"M{m:02d}" for m in range(1, 13)}]
        try:
            vals = [float(d["value"]) for d in months]
        except ValueError:
            fail(f"non-numeric CPI month in {y}")
        if len(vals) != 12:
            fail(f"CPI {y}: {len(vals)} months, need 12")
        out[y] = sum(vals) / 12
        log.info("CPI-U %d annual mean of 12 months = %.4f", y, out[y])
    return out


def load_eia() -> pd.DataFrame:
    path = one("eia/eia_retail_sales_annual_*.json")
    df = pd.DataFrame(json.loads(path.read_text())["data"])
    df = df[df["stateid"].isin(STATES_51) & df["period"].isin([str(Y0), str(Y1)])].copy()
    for c in ("sales", "price"):
        num = pd.to_numeric(df[c], errors="coerce")
        if num.isna().any():
            fail(f"non-numeric EIA {c}: {df.loc[num.isna(), ['stateid', 'period', c]].to_dict('records')}")
        df[c] = num
    if set(df["sales-units"]) != {"million kilowatt hours"} or set(df["price-units"]) != {"cents per kilowatt-hour"}:
        fail(f"unexpected units {set(df['sales-units'])} {set(df['price-units'])}")
    return df


def build(df: pd.DataFrame, sector: str, cpi: dict[int, float]) -> pd.DataFrame:
    d = df[df["sectorid"] == sector]
    if d.duplicated(["stateid", "period"]).any():
        fail(f"{sector}: duplicate state-year")
    s = d.pivot(index="stateid", columns="period", values="sales")
    p = d.pivot(index="stateid", columns="period", values="price")
    out = pd.DataFrame(index=pd.Index(STATES_51, name="state"))
    out["pjm"] = ["full" if st in PJM_FULL else "partial" if st in PJM_PARTIAL else "no" for st in out.index]
    out[f"sales_{Y0}_mwh"] = s[str(Y0)] * MKWH_TO_MWH
    out[f"sales_{Y1}_mwh"] = s[str(Y1)] * MKWH_TO_MWH
    out["sales_change_pct"] = (out[f"sales_{Y1}_mwh"] / out[f"sales_{Y0}_mwh"] - 1) * 100
    out[f"price_nominal_{Y0}_cents"] = p[str(Y0)]
    out[f"price_real_{Y0}_cents"] = p[str(Y0)] * cpi[Y1] / cpi[Y0]
    out[f"price_real_{Y1}_cents"] = p[str(Y1)]
    out["price_change_pct"] = (out[f"price_real_{Y1}_cents"] / out[f"price_real_{Y0}_cents"] - 1) * 100
    out = out.round({f"sales_{Y0}_mwh": 0, f"sales_{Y1}_mwh": 0, "sales_change_pct": 2,
                     f"price_real_{Y0}_cents": 3, "price_change_pct": 2})
    out["sector"] = {"ALL": "all sectors", "RES": "residential"}[sector]
    out["source"] = (f"EIA API v2 electricity/retail-sales (annual), downloaded {path_date()}; "
                     f"prices deflated to {Y1} dollars with BLS CPI-U (CUUR0000SA0) mean of 12 months")
    out = out.reset_index()
    if len(out) != 51 or out.isna().any().any():
        fail(f"{sector}: {len(out)} rows, nulls: {out.isna().sum()[out.isna().sum() > 0].to_dict()}")
    return out


def path_date() -> str:
    return one("eia/eia_retail_sales_annual_*.json").stem.rsplit("_", 1)[-1]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cpi = cpi_annual()
    log.info("deflator CPI_%d / CPI_%d = %.6f", Y1, Y0, cpi[Y1] / cpi[Y0])
    df = load_eia()
    for sector, fname in SECTORS.items():
        out = build(df, sector, cpi)
        out.to_csv(OUT / fname, index=False)
        log.info("wrote %s (%d rows)", fname, len(out))
        show = out.sort_values("sales_change_pct", ascending=False)[
            ["state", "pjm", "sales_change_pct", f"price_real_{Y0}_cents", f"price_real_{Y1}_cents", "price_change_pct"]]
        log.info("%s top/bottom by sales growth:\n%s\n...\n%s", sector,
                 show.head(5).to_string(index=False), show.tail(3).to_string(index=False))
        va = out[out.state == "VA"].iloc[0]
        log.info("%s VA check: sales %d -> %d MWh, nominal price %.2f -> %.2f",
                 sector, va[f"sales_{Y0}_mwh"], va[f"sales_{Y1}_mwh"], va[f"price_nominal_{Y0}_cents"], va[f"price_real_{Y1}_cents"])


if __name__ == "__main__":
    main()
