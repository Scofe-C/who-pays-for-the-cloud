"""Reproduce the Datawrapper/Flourish upload files from data/clean/ and data/manual/facts.csv.

Writes data/upload/<id>.csv, then compares each file to the hand-prepared data/upload_manual/<id>.csv:
same columns, same rows (by key), numbers equal after rounding to the hand file's decimals, strings exact.
Every difference goes to notes/upload_diff_report.md. Exit 0 only if every difference has an entry in
EXPLAINED (file, key, column) -> reason. Neither version is preferred silently.

No figures are typed here: numbers come from data/clean/ or facts.csv (via build_manual_csvs.Facts).
Labels, column headers and the "When" text of the ledger are editorial text and live in this file.
"""

from __future__ import annotations

import csv
import datetime
import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_manual_csvs as bm  # noqa: E402  (reuse load/Facts/display)

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "data" / "upload"
MANUAL = ROOT / "data" / "upload_manual"
REPORT = ROOT / "notes" / "upload_diff_report.md"

log = logging.getLogger("build_uploads")
NOTES: list[str] = []  # facts for the run report (checks passed, pending rows, published-vs-computed)


def fail(msg: str) -> None:
    log.error(msg)
    sys.exit(1)


def read_clean(name: str) -> pd.DataFrame:
    return pd.read_csv(CLEAN / name, dtype={"state": str}, keep_default_na=True)


# ---------------------------------------------------------------- DW1 / DW2
def dw1(_: bm.Facts) -> pd.DataFrame:
    counts = read_clean("dw1_state_counts.csv")
    names = read_clean("dw2_state_share.csv")[["state", "state_name"]]
    out = counts.merge(names, on="state", how="left", validate="one_to_one", indicator=True)
    if (out["_merge"] != "both").any():
        fail(f"DW1: state codes without an EPRI-table name: {out.loc[out._merge != 'both', 'state'].tolist()}")
    if len(out) != 51:
        fail(f"DW1: {len(out)} rows, expected 51")
    return out[["state", "state_name", "facilities", "building_area_km2"]]


def dw2(_: bm.Facts) -> pd.DataFrame:
    d = read_clean("dw2_state_share.csv")
    out = d[["state", "state_name", "dc_mwh_2023", "share_pct_2023"]].copy()
    out["dc_mwh_2023"] = out["dc_mwh_2023"].round().astype("Int64")
    blank = out["dc_mwh_2023"].isna()
    if sorted(out.loc[blank, "state"]) != sorted(d.loc[~d["in_epri_table"], "state"]):
        fail("DW2: blank rows do not match the states missing from the EPRI table")
    if (out["dc_mwh_2023"] == 0).any() or (out["share_pct_2023"] == 0).any():
        fail("DW2: a zero value; states not in the EPRI table must stay blank")
    NOTES.append(f"DW2: {int(blank.sum())} states not in the EPRI table left blank "
                 f"({', '.join(sorted(out.loc[blank, 'state']))}); no zeros.")
    return out


# ---------------------------------------------------------------- DW3
DW3_LABELS = {  # clean utility_area -> label used in the chart
    "Western Maryland (Potomac Edison)": "Western Maryland (Potomac Edison)",
    "Ohio (average)": "Ohio (average)",
    "Pepco (Washington, D.C.)": "Pepco, Washington D.C.*",
    "BGE (Maryland)": "BGE, Maryland",
    "Pepco and SMECO (Maryland)": "Pepco & SMECO, Maryland",
    "PECO (Pennsylvania)": "PECO, Pennsylvania",
}


def dw3(f: bm.Facts) -> pd.DataFrame:
    d = read_clean("dw3_bills.csv")
    if set(d["utility_area"]) != set(DW3_LABELS):
        fail(f"DW3: utilities changed: {sorted(set(d['utility_area']) ^ set(DW3_LABELS))}")
    pepco = d.loc[d.utility_area == "Pepco (Washington, D.C.)", "jump_2025_usd_month"].item()
    if pepco != f.v("ieefa_dc_capacity"):
        fail("DW3: Pepco D.C. 2025 jump is not the capacity portion (ieefa_dc_capacity)")
    bge = d.loc[d.utility_area == "BGE (Maryland)", "jump_2025_usd_month"].item()
    if bge != bm.r2(f.v("mdopc_bge_cumulative") - f.v("mdopc_bge_latest")):
        fail("DW3: BGE 2025 jump != cumulative - latest")
    NOTES.append(f"DW3: Pepco D.C. 2025 jump = {pepco:g} (capacity portion, not the "
                 f"{f.v('ieefa_dc_total'):g} total); BGE 2025 jump = {f.v('mdopc_bge_cumulative'):g} - "
                 f"{f.v('mdopc_bge_latest'):g} = {bge:g}.")
    return pd.DataFrame({
        "Utility": d["utility_area"].map(DW3_LABELS),
        "2025 jump": d["jump_2025_usd_month"],
        "2026 increase": d["increment_2026_usd_month"],
        "2026 net, after credits": d["net_2026_after_credits_usd_month"],
    })


# ---------------------------------------------------------------- DW4
def _usd_b(v: float) -> str:
    return f"${v:g}B"


# side, who, what, fact ids, figure formatter (values in fact-id order), when, source name
DW4 = [
    ("Wins", "Data-center operators (Va.)", "Sales and use tax exemption, self-reported", ["vatax_fy25"],
     lambda v: f"${v[0] / 1e9:.2f}B", "FY2025", "Va. Dept. of Taxation"),
    ("Wins", "Virginia workers", "Jobs supported per year, incl. indirect and induced",
     ["jlarc_jobs_total", "jlarc_jobs_construction"],
     lambda v: f"{v[0]:,.0f} ({v[1]:,.0f} in construction)", "Annual average", "JLARC"),
    ("Pays", "Virginia taxpayers", "State revenue returned per $1 of exemption", ["jlarc_return_per_dollar"],
     lambda v: f"{v[0]:g}¢", "Annual average", "JLARC"),
    ("Pays", "Data-center operators (Va.)", "New electricity consumption tax", ["vabudget_rate", "vabudget_cap"],
     lambda v: f"{v[0] * 100:g}¢/kWh, capped at ${v[1]:g}M a year", "From July 2026",
     "Williams Mullen (HB 30 summary)"),
    ("Pays", "PJM electricity customers", "Capacity charges tied to data-center load, last four auctions",
     ["imm_4auction_dc", "imm_4auction_share"], lambda v: f"{_usd_b(v[0])} ({v[1]:g}% of the total)",
     "Through 2028/29", "Monitoring Analytics"),
    ("Pays", "Households, western Maryland", "Capacity-price effect on average residential bill", ["ieefa_wmd"],
     lambda v: f"+${v[0]:g} a month", "2025/26", "IEEFA"),
    ("Pays", "Households, Maryland (BGE)", "Bill increase, last two auctions combined", ["mdopc_bge_cumulative"],
     lambda v: f"+${v[0]:.2f} a month", "2026/27 vs. 2024/25", "Maryland OPC"),
    ("Context", "U.S. grid", "Data-center share of U.S. electricity", ["lbnl25_2024_share", "lbnl25_2030_mid"],
     lambda v: f"{v[0]:g}% → {v[1]:g}% (projected)", "2024 → 2030", "LBNL 2025 Update"),
    ("Context", "Data-center developers", "Projects blocked or delayed by local opposition", ["dcw_blocked_delayed"],
     lambda v: _usd_b(v[0]), "2023 – Q1 2025", "Data Center Watch"),
]


def source_md(f: bm.Facts, ids: list[str], name: str) -> str:
    rows = [f.row(i) for i in ids]
    pages = sorted({int(r["page"]) for r in rows if r["page"].isdigit()})
    label = name + (f", p. {pages[0]}" if len(pages) == 1 else
                    f", pp. {', '.join(map(str, pages))}" if pages else "")
    return f"[{label}]({rows[0]['source_url']})"


def dw4(f: bm.Facts) -> pd.DataFrame:
    rows = [{"Side": side, "Who": who, "What": what, "Figure": fmt([f.v(i) for i in ids]), "When": when,
             "Source": source_md(f, ids, name)}
            for side, who, what, ids, fmt, when, name in DW4]
    sides = pd.Series([r["Side"] for r in rows]).value_counts().to_dict()
    if sides != {"Wins": 2, "Pays": 5, "Context": 2}:
        fail(f"DW4: side counts {sides} != 2 Wins / 5 Pays / 2 Context")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- F1
def f1(_: bm.Facts) -> pd.DataFrame:
    d = read_clean("f1_donut.csv")
    n_other = len(read_clean("f1_county_share.csv")) - 5
    if d.loc[2, "counties"] != f"{n_other} counties":
        fail(f"F1: 'all other' count {d.loc[2, 'counties']!r} != {n_other} counties from f1_county_share")
    share = d["share_pct"].round(1)
    if abs(share.sum() - 100) > 0.1:
        fail(f"F1: rounded shares sum to {share.sum()}")
    counties = d["counties"].tolist()
    counties[2] = f"{n_other} other counties with mapped data centers"
    return pd.DataFrame({"slice": d["slice"], "share_pct": share,
                         "floor_area": [f"{m / 1e6:.2f} km²" for m in d["building_area_m2"]],
                         "counties": counties})


# ---------------------------------------------------------------- F2 + captions
F2_ORDER = ["Microsoft", "Alphabet", "Amazon", "Meta", "Oracle"]
F2_START = "2018Q3"  # Amazon has no TTM before 2018Q3


def f2_ttm() -> pd.DataFrame:
    d = read_clean("f2_capex_long.csv")
    d = d[d["cal_quarter"] >= F2_START]
    w = d.pivot(index="company", columns="cal_quarter", values="capex_ttm_usd") / 1e9
    if w.isna().any().any():
        fail(f"F2: blank TTM from {F2_START}: {w.columns[w.isna().any()].tolist()}")
    if set(w.index) != set(F2_ORDER):
        fail(f"F2: companies {sorted(w.index)}")
    return w.loc[F2_ORDER]


def qlabel(q: str) -> str:
    return f"{q[:4]} {q[4:]}"


def f2(_: bm.Facts) -> pd.DataFrame:
    w = f2_ttm().round(1)
    out = w.rename(columns=qlabel).reset_index()
    out.insert(1, "category", out["company"])
    return out


def f2_captions(f: bm.Facts) -> pd.DataFrame:
    w = f2_ttm()  # unrounded TTM $B
    q = list(w.columns)
    latest = q[-1]
    rows = []

    # (0) external event, from facts.csv (dated event row)
    ev = f.rows.get("openai_chatgpt_launch")
    if ev is None:
        fail("F2 captions: facts row openai_chatgpt_launch missing")
    day = datetime.date.fromisoformat(ev["value"])
    evq = f"{day.year}Q{(day.month - 1) // 3 + 1}"
    rows.append({"from": qlabel(evq), "to": qlabel(q[q.index(evq) + 2]),
                 "text": f"{day:%b}. {day.year}: ChatGPT launches"})
    if not ev["verified_by"].strip():
        NOTES.append("F2 captions: openai_chatgpt_launch is NOT verified yet (caption kept, flagged).")

    # (1) Amazon and Meta: TTM at 2023 Q4 below their 2022-23 peak
    win = [c for c in q if "2022Q1" <= c <= "2023Q4"]
    for co in ("Amazon", "Meta"):
        peak_q = w.loc[co, win].idxmax()
        if not w.loc[co, "2023Q4"] < w.loc[co, peak_q]:
            fail(f"F2 caption 1 false: {co} 2023Q4 not below its 2022-23 peak")
        NOTES.append(f"F2 caption 1: {co} 2023Q4 {w.loc[co, '2023Q4']:.1f} < peak {w.loc[co, peak_q]:.1f} "
                     f"({peak_q}) -- holds.")
    rows.append({"from": "2023 Q3", "to": "2024 Q1", "text": "2023: Amazon and Meta pull back"})

    # (2) Alphabet overtakes Microsoft at 2025 Q2 and stays above through the latest quarter.
    # Alphabet also led before 2023Q2, so "first" means the last crossing: Microsoft >= Alphabet at 2025Q1.
    gap = w.loc["Alphabet"] - w.loc["Microsoft"]
    after = [c for c in q if c >= "2025Q2"]
    if not (gap["2025Q1"] <= 0 and (gap[after] > 0).all()):
        fail("F2 caption 2 false: Alphabet does not overtake Microsoft at 2025Q2 and stay above")
    earlier = [c for c in q if c < "2025Q1" and gap[c] > 0]
    NOTES.append(f"F2 caption 2: Alphabet - Microsoft = {gap['2025Q1']:.1f} at 2025Q1, > 0 every quarter "
                 f"2025Q2-{latest} -- holds. Note: Alphabet was also ahead {earlier[0]}-{earlier[-1]}, "
                 "so this is a re-take of the lead, not the first time ever.")
    rows.append({"from": "2025 Q2", "to": "2025 Q4", "text": "Alphabet overtakes Microsoft"})

    # (3) Oracle: latest / 2024Q4 >= 7 within under two years
    ratio = w.loc["Oracle", "2026Q3"] / w.loc["Oracle", "2024Q4"]
    if ratio < 7.0:
        fail(f"F2 caption 3 false: Oracle 2026Q3/2024Q4 = {ratio:.2f}")
    NOTES.append(f"F2 caption 3: Oracle 2026Q3/2024Q4 = {w.loc['Oracle', '2026Q3']:.1f}/"
                 f"{w.loc['Oracle', '2024Q4']:.1f} = {ratio:.2f} (7 quarters) -- holds.")
    rows.append({"from": "2026 Q1", "to": "2026 Q3", "text": f"Oracle: {int(ratio)}× in under two years"})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- F3 / F4
F3_PHASES = {"Construction": "Construction (temporary)", "Operations": "Operations (lasting)"}


def f3(_: bm.Facts) -> pd.DataFrame:
    d = read_clean("f3_jobs.csv")
    if not (d["squares"] == d["jobs"] / 1000).all():
        fail("F3: squares != jobs / 1000")
    return pd.DataFrame({"block": "Virginia data-center jobs", "phase": d["phase"].map(F3_PHASES),
                         "jobs": d["jobs"], "icons": d["squares"]})


def f4(f: bm.Facts) -> pd.DataFrame:
    dc4, sh4 = f.v("imm_4auction_dc"), f.v("imm_4auction_share")
    tot4 = dc4 / (sh4 / 100)  # derived: IMM states $ and % for the four auctions, not the total
    dc, tot = f.v("imm_2829_dc"), f.v("imm_2829_total")
    sh = round(dc / tot * 100, 1)
    NOTES.append(f"F4: four-auction total ${tot4:.1f}B is derived = {dc4:g} / {sh4:g}% "
                 "(imm_4auction_dc / imm_4auction_share); IMM does not state it.")
    pub = f.rows.get("imm_2829_share")
    if pub is not None and float(pub["value"]) != sh:
        NOTES.append(f"F4: **IMM p.{pub['page']} states {pub['value']}% for 2028/29**; the file uses the computed "
                     f"{dc:g}/{tot:g} = {dc / tot * 100:.2f}% -> {sh:g}% as instructed. Not changed. "
                     f"(imm_2829_share verified_by: {pub['verified_by'] or 'empty'})")
    return pd.DataFrame([
        {"scope": "Last four auctions (2025/26–2028/29)", "Data centers": sh4, "All other": round(100 - sh4, 1),
         "dc_usd": _usd_b(dc4), "total_usd": f"${tot4:.1f}B"},
        {"scope": "2028/29 auction", "Data centers": sh, "All other": round(100 - sh, 1),
         "dc_usd": _usd_b(dc), "total_usd": _usd_b(tot)},
    ])


# ---------------------------------------------------------------- compare
BUILD = [("dw1", dw1, "state"), ("dw2", dw2, "state"), ("dw3", dw3, "Utility"), ("dw4", dw4, "What"),
         ("f1", f1, "slice"), ("f2", f2, "company"), ("f2_captions", f2_captions, "text"),
         ("f3", f3, "phase"), ("f4", f4, "scope")]

# (file, key, column) -> why the generated and hand versions differ. Filled only after reviewing each diff.
EXPLAINED: dict[tuple[str, str, str], str] = {
    ("dw2", "*", "*"): "no hand-made DW2 upload exists; data/upload/dw2.csv is new",
    ("dw4", "Jobs supported per year, incl. indirect and induced", "Source"):
        "both correct: generated cites the facts.csv evidence pages (PDF p.32 text '74,000 jobs', p.34 text "
        "'59,000 jobs'); hand-made cites p.33, a table showing 59,000 / 15,000 / 74,000. Human picks one",
}


def decimals(s: str) -> int:
    return len(s.split(".")[1]) if "." in s else 0


def same(gen: str, man: str) -> bool:
    if gen == man:
        return True
    try:
        g, m = float(gen), float(man)
    except ValueError:
        return False
    return round(g, decimals(man)) == m


def compare(name: str, key: str) -> list[tuple[str, str, str, str, str]]:
    gen_p, man_p = OUT / f"{name}.csv", MANUAL / f"{name}.csv"
    if not man_p.exists():
        return [(name, "*", "*", "file written", "no hand-made file")]
    g = pd.read_csv(gen_p, dtype=str, keep_default_na=False)
    m = pd.read_csv(man_p, dtype=str, keep_default_na=False)
    diffs = []
    if list(g.columns) != list(m.columns):
        diffs.append((name, "(header)", "(columns)", "|".join(g.columns), "|".join(m.columns)))
    gk, mk = g.set_index(key), m.set_index(key)
    for k in sorted(set(gk.index) ^ set(mk.index)):
        diffs.append((name, k, "(row)", "present" if k in gk.index else "missing",
                      "present" if k in mk.index else "missing"))
    for k in [k for k in gk.index if k in mk.index]:
        for c in [c for c in gk.columns if c in mk.columns]:
            gv, mv = gk.at[k, c], mk.at[k, c]
            if not same(gv, mv):
                diffs.append((name, k, c, gv, mv))
    return diffs


def why(d: tuple) -> str | None:
    return EXPLAINED.get(d[:3]) or EXPLAINED.get((d[0], d[1], "*")) or EXPLAINED.get((d[0], "*", "*"))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    sys.stdout.reconfigure(encoding="utf-8")
    f = bm.Facts(bm.load())
    OUT.mkdir(parents=True, exist_ok=True)
    all_diffs = []
    for name, fn, key in BUILD:
        df = fn(f)
        df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8", lineterminator="\n")
        d = compare(name, key)
        log.info("%-12s %3d rows -> data/upload/%s.csv; %d difference(s) vs upload_manual", name, len(df), name, len(d))
        all_diffs += d

    unexplained = [d for d in all_diffs if not why(d)]
    lines = ["# Upload files: generated vs hand-made", "",
             "Generated by `scripts/build_uploads.py` (data/upload/ vs data/upload_manual/). "
             "Numbers compared after rounding to the hand file's decimals; strings exact.", "",
             f"Differences: **{len(all_diffs)}**, unexplained: **{len(unexplained)}**.", "",
             "| file | row key | column | generated | hand-made | explanation |", "|---|---|---|---|---|---|"]
    for d in all_diffs:
        lines.append("| " + " | ".join(str(x).replace("|", "\\|") for x in d) + f" | {why(d) or '**UNEXPLAINED**'} |")
    lines += ["", "## Checks and notes", ""] + [f"- {n}" for n in NOTES]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    for d in all_diffs:
        print(("  OK  " if why(d) else "  !!  ") + " | ".join(map(str, d)) + (f"  -> {why(d)}" if why(d) else ""))
    for n in NOTES:
        print("note:", n)
    log.info("report -> %s", REPORT.relative_to(ROOT))
    if unexplained:
        log.error("%d unexplained difference(s)", len(unexplained))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
