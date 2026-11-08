"""Task 4: SEC companyfacts capex -> f2_capex_long.csv, f2_capex_race_wide.csv.

Rules (DATA_PIPELINE.md Task 4):
1. Candidate tags in order; one tag per fiscal year (FY + its 3M/6M/9M YTD must share it).
2. 10-Q cash-flow values are YTD: Q1=3M, Q2=6M-3M, Q3=9M-6M, Q4=FY-9M.
3. Same (tag, start, end) in several filings -> keep the most recently filed.
4. Fiscal -> calendar quarter by period END date.
5. TTM = sum of 4 consecutive calendar quarters; blank if any missing.
Periods are identified by start/end dates, never by the filing's fy/fp fields.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "sec"
OUT = ROOT / "data" / "clean"
START_Q = pd.Period("2018Q1", freq="Q")

COMPANIES = {  # ticker: (name, fiscal-year-end month)
    "MSFT": ("Microsoft", 6), "GOOGL": ("Alphabet", 12), "AMZN": ("Amazon", 12),
    "META": ("Meta", 12), "ORCL": ("Oracle", 5),
}
# Gross purchases of PP&E. Amazon moved to ProductiveAssets in 2017 filings.
# PaymentsForProceedsFromProductiveAssets (net of proceeds) is deliberately NOT a candidate.
CANDIDATE_TAGS = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"]
FORMS = {"10-K", "10-Q", "10-K/A", "10-Q/A"}
TOL = 0.005

log = logging.getLogger("clean_sec")


def fail(msg: str) -> None:
    log.error(msg)
    sys.exit(1)


def months(start: pd.Timestamp, end: pd.Timestamp) -> int:
    return round(((end - start).days + 1) / 30.44)


def load_facts(path: Path) -> tuple[int, pd.DataFrame]:
    j = json.loads(path.read_text())
    g = j["facts"]["us-gaap"]
    frames = []
    for tag in CANDIDATE_TAGS:
        if tag in g:
            d = pd.DataFrame(g[tag]["units"]["USD"])
            d["tag"] = tag
            frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df = df[df["form"].isin(FORMS) & df["start"].notna()].copy()
    df["start"] = pd.to_datetime(df["start"])
    df["end"] = pd.to_datetime(df["end"])
    df["filed"] = pd.to_datetime(df["filed"])
    df["m"] = [months(s, e) for s, e in zip(df["start"], df["end"])]
    # Rule 3: keep the most recently filed value per (tag, start, end).
    df = df.sort_values("filed").drop_duplicates(["tag", "start", "end"], keep="last")
    return int(j["cik"]), df


def derive_quarters(ticker: str, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    name, fye = COMPANIES[ticker]
    fy = df[(df["m"] == 12) & (df["end"].dt.month == fye)]
    starts = sorted(set(fy["start"]))
    # Current partial fiscal year: no FY fact yet; start = last FY end + 1 day.
    last_end = fy["end"].max()
    starts.append(last_end + pd.Timedelta(days=1))

    rows, fy_rows = [], []
    for s in starts:
        # Rule 1: first candidate tag carrying this FY's 12M fact; for the current partial
        # year (no 12M fact anywhere), first tag carrying its 3M fact.
        tag = None
        for need in (12, 3):
            for t in CANDIDATE_TAGS:
                if not df[(df["tag"] == t) & (df["start"] == s) & (df["m"] == need)].empty:
                    tag = t
                    break
            if tag:
                break
        if tag is None:
            continue
        ytd = {m: df[(df["tag"] == tag) & (df["start"] == s) & (df["m"] == m)] for m in (3, 6, 9, 12)}
        for m, d in ytd.items():
            if len(d) > 1:
                fail(f"{ticker} FY start {s.date()}: {len(d)} {m}M facts")
        ytd = {m: (d.iloc[0] if len(d) else None) for m, d in ytd.items()}
        if ytd[12] is not None:
            fy_rows.append({"company": name, "fy_end": ytd[12]["end"].date(), "annual_usd": int(ytd[12]["val"]),
                            "tag": tag, "accn": ytd[12]["accn"]})
        prev = None
        for qi, m in enumerate((3, 6, 9, 12), 1):
            cur = ytd[m]
            if cur is not None and (qi == 1 or prev is not None):
                val = cur["val"] - (prev["val"] if prev is not None else 0)
                rows.append({
                    "company": name, "ticker": ticker,
                    "cal_quarter": pd.Period(cur["end"], freq="Q"),
                    "fiscal_q": f"FY{(s + pd.DateOffset(years=1)).year if fye != 12 else s.year}Q{qi}",
                    "period_end": cur["end"].date(), "capex_q_usd": int(val), "tag": tag,
                    "filed": cur["filed"].date(), "accn": cur["accn"], "fy_start": s.date(),
                })
            prev = cur
    q = pd.DataFrame(rows)
    if q["cal_quarter"].duplicated().any():
        fail(f"{ticker}: duplicate calendar quarter {q.loc[q['cal_quarter'].duplicated(), 'cal_quarter'].tolist()}")
    return q.sort_values("cal_quarter").reset_index(drop=True), pd.DataFrame(fy_rows)


def add_ttm(q: pd.DataFrame) -> pd.DataFrame:
    s = q.set_index("cal_quarter")["capex_q_usd"]
    ttm = []
    for p in q["cal_quarter"]:
        window = [p - k for k in range(4)]
        ttm.append(int(sum(s[w] for w in window)) if all(w in s.index for w in window) else None)
    q["capex_ttm_usd"] = pd.array(ttm, dtype="Int64")
    return q


def checks(ticker: str, q: pd.DataFrame, fys: pd.DataFrame, df: pd.DataFrame) -> list[str]:
    notes = []
    if (q["capex_q_usd"] < 0).any():
        fail(f"{ticker}: negative quarter {q.loc[q['capex_q_usd'] < 0, ['cal_quarter', 'capex_q_usd']].to_dict('records')}")
    # Spec check (an identity by construction, Q4 = FY - 9M): 4 derived quarters sum to FY.
    for r in fys.itertuples():
        qs = q[(q["fy_start"] == (pd.Timestamp(r.fy_end) - pd.DateOffset(years=1) + pd.Timedelta(days=1)).date())]
        if len(qs) == 4 and abs(qs["capex_q_usd"].sum() - r.annual_usd) > TOL * r.annual_usd:
            fail(f"{ticker} FY{r.fy_end}: quarters sum {qs['capex_q_usd'].sum()} != annual {r.annual_usd}")
    # Real check 1: derived quarters vs separately filed discrete 3M facts (not starting at FY start).
    # Scope: quarters feeding the output (2017Q2 onward, needed for 2018Q1 TTM).
    window_start = (START_Q - 3).start_time
    d3 = df[(df["m"] == 3) & (df["start"] >= window_start)].assign(period_end=lambda x: x["end"].dt.date)
    disc = d3.merge(q[["period_end", "capex_q_usd", "fy_start"]], on="period_end", how="inner")
    disc = disc[disc["start"].dt.date != disc["fy_start"]]
    bad = disc[(disc["val"] - disc["capex_q_usd"]).abs() > TOL * disc["val"]]
    notes.append(f"discrete-3M cross-check: {len(disc)} compared, {len(bad)} off by >0.5%")
    if len(bad):
        fail(f"{ticker}: derived quarter disagrees with filed 3M fact:\n{bad[['start', 'end', 'val', 'capex_q_usd', 'filed']]}")
    # Real check 2: computed TTM vs reported trailing-12M facts that are not fiscal years (Amazon 10-Qs).
    fye = COMPANIES[ticker][1]
    rep = df[(df["m"] == 12) & (df["end"].dt.month != fye) & (df["end"] >= START_Q.start_time)].copy()
    if len(rep):
        rep["cal_quarter"] = [pd.Period(e, freq="Q") for e in rep["end"]]
        m = rep.merge(q[["cal_quarter", "capex_ttm_usd"]], on="cal_quarter").dropna(subset=["capex_ttm_usd"])
        badt = m[(m["val"] - m["capex_ttm_usd"].astype(float)).abs() > TOL * m["val"]]
        notes.append(f"reported-TTM cross-check: {len(m)} compared, {len(badt)} off by >0.5%")
        if len(badt):
            fail(f"{ticker}: computed TTM disagrees with reported TTM:\n{badt[['end', 'val', 'capex_ttm_usd']]}")
    return notes


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    all_q, all_fy = [], []
    for ticker in COMPANIES:
        path = next(RAW.glob(f"sec_companyfacts_{ticker}_CIK*.json"))
        cik, df = load_facts(path)
        q, fys = derive_quarters(ticker, df)
        q = add_ttm(q)
        for n in checks(ticker, q, fys, df):
            log.info("%s %s", ticker, n)
        tag_use = q[q["cal_quarter"] >= START_Q - 3].groupby("tag")["cal_quarter"].agg(["min", "max", "count"])
        log.info("%s tag usage (quarters):\n%s", ticker, tag_use.to_string())
        fys["url"] = [f"https://www.sec.gov/Archives/edgar/data/{cik}/{a.replace('-', '')}/{a}-index.htm" for a in fys["accn"]]
        all_q.append(q)
        all_fy.append(fys)

    q = pd.concat(all_q, ignore_index=True)
    q = q[q["cal_quarter"] >= START_Q].copy()
    latest = q["cal_quarter"].max()
    q["cal_quarter"] = q["cal_quarter"].astype(str)

    # Gaps inside range -> report (TTM will be blank there).
    for c, g in q.groupby("company"):
        full = pd.period_range(START_Q, latest, freq="Q").astype(str)
        miss = sorted(set(full) - set(g["cal_quarter"]))
        blank = g.loc[g["capex_ttm_usd"].isna(), "cal_quarter"].tolist()
        log.info("%s: %s..%s, missing quarters %s, blank TTM %s", c, g.cal_quarter.min(), g.cal_quarter.max(), miss, blank)

    q["source"] = "SEC EDGAR XBRL companyfacts (10-K/10-Q cash-flow statement), downloaded " + \
        next(RAW.glob("sec_companyfacts_MSFT_*.json")).stem.rsplit("_", 1)[-1]
    long = q[["company", "cal_quarter", "capex_q_usd", "capex_ttm_usd", "tag", "filed",
              "fiscal_q", "period_end", "accn", "source"]].sort_values(["company", "cal_quarter"])
    long.to_csv(OUT / "f2_capex_long.csv", index=False)

    wide = (long.assign(ttm_b=(long["capex_ttm_usd"].astype("Float64") / 1e9).round(3))
                .pivot(index="company", columns="cal_quarter", values="ttm_b"))
    wide = wide[sorted(wide.columns)].reindex([v[0] for v in COMPANIES.values()]).reset_index()
    wide.to_csv(OUT / "f2_capex_race_wide.csv", index=False)
    # Flourish race without the quarters where Amazon's TTM is blank (no gross 2017 6M fact).
    drop = [c for c in wide.columns if c in ("2018Q1", "2018Q2")]
    wide.drop(columns=drop).to_csv(OUT / "f2_capex_race_wide_from2018Q3.csv", index=False)
    log.info("wrote f2_capex_race_wide_from2018Q3.csv (dropped %s)", drop)
    log.info("wrote f2_capex_long.csv (%d rows), f2_capex_race_wide.csv (%d x %d)",
             len(long), len(wide), wide.shape[1] - 1)

    fy = pd.concat(all_fy, ignore_index=True)
    fy = fy[pd.to_datetime(fy["fy_end"]) >= "2017-06-01"]
    pd.set_option("display.width", 250)
    pd.set_option("display.max_colwidth", 120)
    log.info("FY summary (spot-check any row):\n%s",
             fy[["company", "fy_end", "annual_usd", "tag", "url"]].to_string(index=False))
    log.info("latest TTM $B:\n%s", wide[["company", str(latest)]].to_string(index=False))


if __name__ == "__main__":
    main()
