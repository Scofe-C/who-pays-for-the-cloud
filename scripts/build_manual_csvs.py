"""Task 8: chart CSVs built from data/manual/facts.csv only (no typed figures).

Outputs (data/clean/): h1_pjm, h2_va_tax, h3_forecasts, p3_iea, f3_jobs, f4_imm, dw3_bills, dw4_ledger.
Rules:
- Every value comes from a facts.csv row; its id is kept in a `fact_id` column.
- A value computed from two facts (difference, ratio) carries all ids in `fact_id` joined by '+'
  and a `derivation` text. Unit conversions (/1000 etc.) are labeled too.
- Every fact used must have `verified_by` filled; otherwise the build stops.
- A figure the facts do not contain is left blank and logged, never filled.
"""

from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACTS = ROOT / "data" / "manual" / "facts.csv"
OUT = ROOT / "data" / "clean"

log = logging.getLogger("build_manual_csvs")


def fail(msg: str) -> None:
    log.error(msg)
    sys.exit(1)


def load() -> dict[str, dict]:
    raw = FACTS.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        fail("facts.csv is not UTF-8 (was it saved from Excel?). Restore UTF-8 before building.")
    rows = list(csv.DictReader(text.splitlines()))
    return {r["id"]: r for r in rows}


class Facts:
    def __init__(self, rows: dict[str, dict]):
        self.rows = rows
        self.used: set[str] = set()

    def row(self, fid: str) -> dict:
        if fid not in self.rows:
            fail(f"fact {fid!r} not in facts.csv")
        r = self.rows[fid]
        if not r["verified_by"].strip():
            fail(f"fact {fid!r} has no verified_by; a human must verify it first")
        self.used.add(fid)
        return r

    def v(self, fid: str) -> float:
        return float(self.row(fid)["value"])

    def has(self, fid: str) -> bool:
        return fid in self.rows

    def src(self, fid: str) -> dict:
        r = self.row(fid)
        return {"source_title": r["source_title"], "source_url": r["source_url"], "page": r["page"], "as_of": r["as_of"]}


def r2(x: float) -> float:
    """Round derived arithmetic to 2 decimals (inputs have at most 2)."""
    return round(x, 2)


def write(name: str, rows: list[dict]) -> None:
    cols: list[str] = []
    for r in rows:
        cols += [k for k in r if k not in cols]
    with (OUT / name).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    log.info("wrote %s (%d rows)", name, len(rows))


def h1_pjm(f: Facts) -> list[dict]:
    out = []
    for fid, year in [("pjm_2425", "2024/25"), ("pjm_2526", "2025/26"), ("pjm_2627", "2026/27"),
                      ("pjm_2728", "2027/28"), ("pjm_2829", "2028/29")]:
        r = f.row(fid)
        # at_cap only where the source states it (fact notes); otherwise unknown -> blank.
        at_cap = "True" if "cleared at the price cap" in r["notes"] else ""
        row = {"delivery_year": year, "price_usd_mw_day": f.v(fid), "at_cap": at_cap,
               "uncapped_sim_usd_mw_day": "", "fact_id": fid, "uncapped_fact_id": "",
               "at_cap_fact_id": "", "at_cap_source": ""}
        # 2026/27: the 2028/29 report does not say it hit the cap; the 2026/27 report does
        # (pjm_2627_at_cap). Used only once a human has verified that row.
        if year == "2026/27":
            cap = f.rows.get("pjm_2627_at_cap")
            if cap is not None and cap["verified_by"].strip() and cap["value"] == "true":
                c = f.row("pjm_2627_at_cap")
                row.update(at_cap="True", at_cap_fact_id="pjm_2627_at_cap",
                           at_cap_source=f"{c['source_title']}, p. {c['page']}")
            else:
                log.warning("H1: pjm_2627_at_cap missing or unverified -> 2026/27 at_cap left blank")
        if year == "2028/29":
            row["uncapped_sim_usd_mw_day"] = f.v("pjm_2829_uncapped")
            row["uncapped_fact_id"] = "pjm_2829_uncapped"
        row.update(f.src(fid))
        out.append(row)
    blank = [r["delivery_year"] for r in out if not r["at_cap"]]
    log.info("H1 at_cap blank (source does not state it) for %s", blank)
    return out


def h2_va_tax(f: Facts) -> list[dict]:
    out = []
    for fid, fy in [("jlarc_fy23_exemption", "FY2023"), ("vatax_fy24", "FY2024"), ("vatax_fy25", "FY2025")]:
        unit = f.row(fid)["unit"]
        usd = f.v(fid) * (1e6 if unit == "USD million" else 1)
        out.append({"series": "exemption_benefit", "period": fy, "value_usd_b": round(usd / 1e9, 4),
                    "value_as_reported": f.v(fid), "unit_as_reported": unit, "fact_id": fid,
                    "derivation": "unit conversion to USD billion",
                    "label_note": "self-reported by data center operators; state + local", **f.src(fid)})
    out.append({"series": "new_tax_annual_cap", "period": f.row("vabudget_cap")["period"],
                "value_usd_b": round(f.v("vabudget_cap") * 1e6 / 1e9, 4), "value_as_reported": f.v("vabudget_cap"),
                "unit_as_reported": f.row("vabudget_cap")["unit"], "fact_id": "vabudget_cap",
                "derivation": "unit conversion to USD billion", "label_note": "secondary source (HB 30 budget)",
                **f.src("vabudget_cap")})
    for fid in ("vabudget_rate", "jlarc_return_per_dollar"):
        out.append({"series": fid, "period": f.row(fid)["period"], "value_usd_b": "",
                    "value_as_reported": f.v(fid), "unit_as_reported": f.row(fid)["unit"], "fact_id": fid,
                    "derivation": "", "label_note": f.row(fid)["metric"], **f.src(fid)})
    return out


def h3_forecasts(f: Facts) -> list[dict]:
    out = []
    for fid, year in [("lbnl24_2023_share", 2023), ("lbnl25_2024_share", 2024)]:
        out.append({"kind": "actual", "report": f.row(fid)["source_title"], "target_year": year,
                    "low_pct": "", "high_pct": "", "point_pct": f.v(fid), "unit": f.row(fid)["unit"],
                    "fact_id": fid, **f.src(fid)})
    ranges = [("LBNL 2024", 2024, 2028, "lbnl24_2028_low", "lbnl24_2028_high", None),
              ("EPRI 2024", 2024, 2030, "epri24_2030_low", "epri24_2030_high", None),
              ("LBNL 2025 Update", 2025, 2030, "lbnl25_2030_low", "lbnl25_2030_high", "lbnl25_2030_mid"),
              ("EPRI 2026", 2026, 2030, "epri26_2030_low", "epri26_2030_high", None)]
    for name, ry, ty, lo, hi, mid in ranges:
        ids = [lo, hi] + ([mid] if mid else [])
        out.append({"kind": "forecast_range", "report": name, "report_year": ry, "target_year": ty,
                    "low_pct": f.v(lo), "high_pct": f.v(hi), "point_pct": f.v(mid) if mid else "",
                    "unit": f.row(lo)["unit"], "fact_id": "+".join(ids), **f.src(lo)})
    return out


def p3_iea(f: Facts) -> list[dict]:
    items = [("iea25_2024_twh", 2024, "estimate"), ("iea26_2025_twh", 2025, "estimate"),
             ("iea26_2030_twh", 2030, "projection (Base Case)")]
    r23 = f.rows.get("iea26_2023_twh")
    if r23 is None:
        log.warning("P3: iea26_2023_twh not in facts.csv -> 2023 omitted")
    elif not r23["verified_by"].strip():
        log.warning("P3: iea26_2023_twh not yet verified -> 2023 omitted until a human verifies it")
    else:
        items.insert(0, ("iea26_2023_twh", 2023, "estimate"))
    return [{"year": year, "twh": f.v(fid), "kind": kind, "report": f.row(fid)["source_title"],
             "fact_id": fid, "notes": f.row(fid)["notes"], **f.src(fid)} for fid, year, kind in items]


def f3_jobs(f: Facts) -> list[dict]:
    c, o, t = f.v("jlarc_jobs_construction"), f.v("jlarc_jobs_operations"), f.v("jlarc_jobs_total")
    if c + o != t:
        fail(f"F3: construction {c} + operations {o} != total {t}")
    log.info("F3 check ok: %d + %d = %d", c, o, t)
    return [{"phase": phase, "jobs": int(f.v(fid)), "squares": int(f.v(fid) / 1000), "fact_id": fid,
             "derivation": "squares = jobs / 1000 (one square per 1,000 jobs)", **f.src(fid)}
            for phase, fid in [("Construction", "jlarc_jobs_construction"), ("Operations", "jlarc_jobs_operations")]]


def f4_imm(f: Facts) -> list[dict]:
    dc, tot = f.v("imm_2829_dc"), f.v("imm_2829_total")
    computed = r2(dc / tot * 100)
    row = {"scope": "2028/29 auction", "data_center_usd_b": dc, "other_usd_b": r2(tot - dc), "total_usd_b": tot,
           "data_center_pct": computed, "other_pct": r2(100 - computed), "fact_id": "imm_2829_dc+imm_2829_total",
           "derivation": "other = total - data center; pct = data center / total", "notes": "",
           **f.src("imm_2829_dc")}
    pub = f.rows.get("imm_2829_share")
    if pub is not None and pub["verified_by"].strip():
        share = f.v("imm_2829_share")
        row.update(data_center_pct=share, other_pct=r2(100 - share), fact_id=row["fact_id"] + "+imm_2829_share",
                   derivation="other = total - data center; data_center_pct = IMM published; other_pct = 100 - published",
                   notes=f"computed share {dc:g} / {tot:g} = {computed}% (IMM rounds inputs); chart uses IMM's {share:g}%")
    else:
        log.warning("F4: imm_2829_share missing or unverified -> using computed share %.2f%%", computed)
        row["notes"] = "computed share; IMM's published share (imm_2829_share) awaits verification"
    out = [row]
    share = f.v("imm_4auction_share")
    four = {"scope": "Last four auctions", "data_center_usd_b": f.v("imm_4auction_dc"), "other_usd_b": "",
            "total_usd_b": "", "data_center_pct": share, "other_pct": r2(100 - share),
            "fact_id": "imm_4auction_dc+imm_4auction_share", "derivation": "other_pct = 100 - data center pct",
            "notes": "IMM does not state the four-auction USD total; USD other/total left blank",
            **f.src("imm_4auction_dc")}
    if f.has("imm_4auction_total"):
        t4 = f.v("imm_4auction_total")
        four.update(total_usd_b=t4, other_usd_b=r2(t4 - four["data_center_usd_b"]),
                    fact_id=four["fact_id"] + "+imm_4auction_total")
        four["derivation"] += "; other = total - data center"
    else:
        log.warning("F4: imm_4auction_total not in facts.csv -> four-auction total/other USD left blank")
    out.append(four)
    return out


def dw3_bills(f: Facts) -> list[dict]:
    bge_cum, bge_latest = f.v("mdopc_bge_cumulative"), f.v("mdopc_bge_latest")
    rows = [
        {"utility_area": "Western Maryland (Potomac Edison)", "jump_2025_usd_month": f.v("ieefa_wmd"),
         "increment_2026_usd_month": "", "net_2026_after_credits_usd_month": "", "fact_id": "ieefa_wmd",
         "measure": f.row("ieefa_wmd")["metric"], "derivation": "", **f.src("ieefa_wmd")},
        {"utility_area": "Ohio (average)", "jump_2025_usd_month": f.v("ieefa_oh"),
         "increment_2026_usd_month": "", "net_2026_after_credits_usd_month": "", "fact_id": "ieefa_oh",
         "measure": f.row("ieefa_oh")["metric"], "derivation": "", **f.src("ieefa_oh")},
        {"utility_area": "Pepco (Washington, D.C.)", "jump_2025_usd_month": f.v("ieefa_dc_capacity"),
         "increment_2026_usd_month": "", "net_2026_after_credits_usd_month": "",
         "total_bill_increase_usd_month": f.v("ieefa_dc_total"),
         "fact_id": "ieefa_dc_capacity+ieefa_dc_total",
         "measure": "capacity-price portion of the bill increase (DC OPC estimate); total increase in its own column",
         "derivation": "", **f.src("ieefa_dc_total")},
        {"utility_area": "BGE (Maryland)", "jump_2025_usd_month": r2(bge_cum - bge_latest),
         "increment_2026_usd_month": bge_latest, "net_2026_after_credits_usd_month": f.v("mdopc_bge_net"),
         "fact_id": "mdopc_bge_cumulative+mdopc_bge_latest+mdopc_bge_net",
         "measure": "residential bill change from capacity auctions (MD OPC)",
         "derivation": "jump_2025 = cumulative (2026/27 vs 2024/25) - latest (2026/27 vs 2025/26)",
         **f.src("mdopc_bge_cumulative")},
        {"utility_area": "Pepco and SMECO (Maryland)", "jump_2025_usd_month": "", "increment_2026_usd_month": "",
         "net_2026_after_credits_usd_month": f.v("mdopc_pepco_net"), "fact_id": "mdopc_pepco_net",
         "measure": f.row("mdopc_pepco_net")["metric"], "derivation": "", **f.src("mdopc_pepco_net")},
        {"utility_area": "PECO (Pennsylvania)", "jump_2025_usd_month": "", "increment_2026_usd_month": f.v("peco_2026_usd"),
         "net_2026_after_credits_usd_month": "", "fact_id": "peco_2026_usd",
         "measure": f"typical bill increase (700 kWh), {f.v('peco_2026_pct'):g}%; secondary source",
         "derivation": "", **f.src("peco_2026_usd")},
    ]
    f.row("peco_2026_pct")
    return rows


# side, who, what -- editorial classification (DRAFT for human review); figures come from facts.csv.
LEDGER = [
    ("Wins", "Data center operators (Virginia)", "Sales and use tax exemption benefit, self-reported", "jlarc_fy23_exemption"),
    ("Wins", "Data center operators (Virginia)", "Sales and use tax exemption benefit, self-reported", "vatax_fy24"),
    ("Wins", "Data center operators (Virginia)", "Sales and use tax exemption benefit, self-reported", "vatax_fy25"),
    ("Wins", "Virginia workers", "Jobs supported during construction (incl. indirect + induced)", "jlarc_jobs_construction"),
    ("Wins", "Virginia workers", "Jobs supported during operations (incl. indirect + induced)", "jlarc_jobs_operations"),
    ("Pays", "Virginia taxpayers", "State revenue returned per $1 of exemption", "jlarc_return_per_dollar"),
    ("Pays", "Data center operators (Virginia)", "New electricity consumption tax rate", "vabudget_rate"),
    ("Pays", "Data center operators (Virginia)", "Annual cap on the new tax's revenue", "vabudget_cap"),
    ("Pays", "PJM electricity customers", "Capacity charges from data center load, last four auctions", "imm_4auction_dc"),
    ("Pays", "PJM electricity customers", "Data center share of capacity charges, last four auctions", "imm_4auction_share"),
    ("Pays", "PJM electricity customers", "Capacity charges from data center load, 2028/29 auction", "imm_2829_dc"),
    ("Pays", "Households, western Maryland", "Capacity-price effect on average residential bill", "ieefa_wmd"),
    ("Pays", "Households, Ohio", "Capacity-price effect on average residential bill", "ieefa_oh"),
    ("Pays", "Households, Washington D.C. (Pepco)", "Average residential bill increase", "ieefa_dc_total"),
    ("Pays", "Households, Maryland (BGE)", "Bill increase, last two auctions combined", "mdopc_bge_cumulative"),
    ("Pays", "Households, Pennsylvania (PECO)", "Typical residential bill increase", "peco_2026_usd"),
    ("Context", "Data center projects", "Projects blocked or delayed by local opposition", "dcw_blocked_delayed"),
    ("Context", "U.S. grid", "Data center share of U.S. electricity", "lbnl25_2024_share"),
    ("Context", "U.S. grid", "Projected data center share of U.S. electricity, Reference Case", "lbnl25_2030_mid"),
]


# One row per "who", strongest figure each (picked with the human, 2026-11-07).
LEDGER_SHORT = ["vatax_fy25", "jlarc_jobs_construction", "jlarc_return_per_dollar", "imm_4auction_dc",
                "ieefa_dc_total", "ieefa_wmd", "dcw_blocked_delayed", "lbnl25_2030_mid"]


def display(value: str, unit: str) -> str:
    """Human-readable figure for tables; formatting only, the number is the fact's value."""
    v = float(value)
    if unit == "USD":
        return f"${v / 1e9:.2f}B" if v >= 1e9 else f"${v / 1e6:.1f}M"
    if unit == "USD million":
        return f"${v:,.1f}M"
    if unit == "USD million per year":
        return f"${v:,.0f}M a year"
    if unit == "USD billion":
        return f"${v:g}B"
    if unit == "USD per kWh":
        return f"{v * 100:g}¢/kWh"
    if unit == "USD per month":
        return f"${v:g}/month"
    if unit.startswith("cents"):
        return f"{v:g}¢"
    if unit.startswith("%"):
        return f"{v:g}%"
    if unit == "jobs per year":
        return f"{v:,.0f} jobs"
    fail(f"display: no format for unit {unit!r}")


def dw4_ledger(f: Facts) -> list[dict]:
    out = []
    for side, who, what, fid in LEDGER:
        r = f.row(fid)
        out.append({"side": side, "who": who, "what": what, "display": display(r["value"], r["unit"]),
                    "value": r["value"], "unit": r["unit"], "period": r["period"], "fact_id": fid, **f.src(fid)})
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    f = Facts(load())
    for name, fn in [("h1_pjm.csv", h1_pjm), ("h2_va_tax.csv", h2_va_tax), ("h3_forecasts.csv", h3_forecasts),
                     ("p3_iea.csv", p3_iea), ("f3_jobs.csv", f3_jobs), ("f4_imm.csv", f4_imm),
                     ("dw3_bills.csv", dw3_bills), ("dw4_ledger.csv", dw4_ledger)]:
        rows = fn(f)
        write(name, rows)
        if name == "dw4_ledger.csv":
            by_id = {r["fact_id"]: r for r in rows}
            missing = [i for i in LEDGER_SHORT if i not in by_id]
            if missing:
                fail(f"DW4 short: picks not in ledger: {missing}")
            write("dw4_ledger_short.csv", [by_id[i] for i in LEDGER_SHORT])
    log.info("facts used: %d of %d", len(f.used), len(f.rows))


if __name__ == "__main__":
    main()
