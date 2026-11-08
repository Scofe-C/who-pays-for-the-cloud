"""Task 5: PNNL IM3 Data Center Atlas -> dw1_state_counts.csv, f1_county_share.csv, f1_donut.csv.

Input (read-only): data/raw/im3_open_source_data_center_atlas_v2026.02.09.csv
Area source: CSV `sqft` field (2-D building footprint area, NOT multi-storey floor area). Validated against GeoPackage building
polygons with a local equal-area approximation (ratio 0.997-1.003); see notes/cleaning_log.md.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "im3_open_source_data_center_atlas_v2026.02.09.csv"
OUT = ROOT / "data" / "clean"

ATLAS_VERSION = "v2026.02.09"
SQFT_TO_M2 = 0.09290304  # exact: 1 ft = 0.3048 m
ATTRIBUTION = (
    "PNNL IM3 Open Source Data Center Atlas " + ATLAS_VERSION
    + " (https://www.osti.gov/biblio/2550666); © OpenStreetMap contributors; ODbL 1.0"
)
LOUDOUN_FIPS = "51107"

STATES_51 = (
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV "
    "NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY"
).split()

log = logging.getLogger("clean_im3")


def fail(msg: str) -> None:
    log.error(msg)
    sys.exit(1)


def load() -> pd.DataFrame:
    df = pd.read_csv(RAW, dtype={"id": str, "state_id": str, "county_id": str})
    log.info("rows in: %d (%s)", len(df), df["type"].value_counts().to_dict())
    df["county_fips"] = df["state_id"].str.zfill(2) + df["county_id"].str.zfill(3)
    return df


def drop_non_states(df: pd.DataFrame) -> pd.DataFrame:
    extra = df[~df["state_abb"].isin(STATES_51)]
    if len(extra):
        log.info("dropped %d rows outside 50 states + DC: %s", len(extra),
                 extra["state_abb"].value_counts().to_dict())
    return df[df["state_abb"].isin(STATES_51)].copy()


def dedupe(df: pd.DataFrame, keep: str) -> pd.DataFrame:
    """Same id appears once per county a feature straddles. Keep one row per id.

    keep='first' keeps the lowest county_fips, 'last' the highest (used for sensitivity check).
    """
    dups = df[df["id"].duplicated(keep=False)]
    if dups.groupby("id")["state_abb"].nunique().gt(1).any():
        fail("duplicate id spans two states; state counts would be ambiguous")
    out = df.sort_values(["id", "county_fips"]).drop_duplicates("id", keep=keep)
    return out


def state_counts(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("state_abb")
    out = pd.DataFrame({
        "facilities": g["id"].nunique(),
        "n_point": g["type"].apply(lambda s: (s == "point").sum()),
        "n_building": g["type"].apply(lambda s: (s == "building").sum()),
        "n_campus": g["type"].apply(lambda s: (s == "campus").sum()),
    })
    bld = df[df["type"] == "building"].groupby("state_abb")["sqft"].sum()
    out["building_area_km2"] = (bld * SQFT_TO_M2 / 1e6).round(4)
    # States absent from the atlas: 0 mapped records (an observed count, not an estimate).
    out = out.reindex(STATES_51)
    zero_states = out.index[out["facilities"].isna()].tolist()
    out = out.fillna(0)
    for c in ["facilities", "n_point", "n_building", "n_campus"]:
        out[c] = out[c].astype(int)
    out = out.reset_index().rename(columns={"state_abb": "state"})
    out["attribution"] = ATTRIBUTION
    log.info("states with zero mapped records: %s", zero_states)
    return out[["state", "facilities", "building_area_km2", "n_point", "n_building",
                "n_campus", "attribution"]]


def county_share(df: pd.DataFrame) -> pd.DataFrame:
    b = df[df["type"] == "building"]
    log.info("buildings after dedupe: %d", len(b))
    if b["sqft"].isna().any():
        fail("building rows with missing sqft")
    g = (b.groupby(["county_fips", "county", "state_abb"], as_index=False)["sqft"].sum()
           .rename(columns={"county": "county", "state_abb": "state"}))
    if g["county_fips"].duplicated().any():
        fail("county_fips maps to more than one county name")
    g["building_area_m2"] = (g["sqft"] * SQFT_TO_M2).round(1)
    total = g["sqft"].sum()
    g["share_pct"] = (g["sqft"] / total * 100).round(4)
    g = g.sort_values("sqft", ascending=False).reset_index(drop=True)
    g["rank"] = g.index + 1
    g["attribution"] = ATTRIBUTION
    return g[["county_fips", "county", "state", "building_area_m2", "share_pct", "rank",
              "attribution", "sqft"]]


def donut(cs: pd.DataFrame) -> pd.DataFrame:
    if cs.loc[0, "county_fips"] != LOUDOUN_FIPS:
        fail(f"rank 1 is {cs.loc[0, 'county']} {cs.loc[0, 'state']}, not Loudoun; donut spec invalid")
    total = cs["sqft"].sum()
    parts = [
        ("Loudoun County, VA", cs.iloc[:1]),
        ("Next 4 counties", cs.iloc[1:5]),
        ("All other counties", cs.iloc[5:]),
    ]
    rows = [{
        "slice": name,
        "counties": ", ".join(f"{r.county} {r.state}" for r in p.itertuples()) if len(p) <= 4 else f"{len(p)} counties",
        "building_area_m2": round(p["sqft"].sum() * SQFT_TO_M2, 1),
        "share_pct": round(p["sqft"].sum() / total * 100, 2),
        "attribution": ATTRIBUTION,
    } for name, p in parts]
    return pd.DataFrame(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    OUT.mkdir(parents=True, exist_ok=True)
    df = drop_non_states(load())
    n0 = len(df)
    dd = dedupe(df, keep="first")
    log.info("dedupe by id: %d -> %d (removed %d)", n0, len(dd), n0 - len(dd))

    sc = state_counts(dd)
    cs = county_share(dd)
    dn = donut(cs)

    # Sensitivity: assign straddling buildings to the other county instead.
    alt = county_share(dedupe(df, keep="last"))
    same_top5 = set(alt["county_fips"][:5]) == set(cs["county_fips"][:5])
    top5_cs, top5_alt = cs["share_pct"][:5].sum(), alt["share_pct"][:5].sum()
    log.info("dedupe sensitivity: top-5 membership unchanged=%s; top-5 share %.2f%% vs %.2f%%",
             same_top5, top5_cs, top5_alt)

    # Acceptance checks
    if len(sc) != 51:
        fail(f"state rows = {len(sc)}, expected 51")
    if abs(cs["share_pct"].sum() - 100) > 0.1:
        fail(f"county shares sum to {cs['share_pct'].sum()}")
    if abs(dn["share_pct"].sum() - 100) > 0.1:
        fail(f"donut shares sum to {dn['share_pct'].sum()}")
    if not cs["county_fips"].str.fullmatch(r"\d{5}").all():
        fail("county_fips not 5-digit strings")
    if sc.isna().any().any() or cs.isna().any().any():
        fail("nulls in output")

    sc.to_csv(OUT / "dw1_state_counts.csv", index=False)
    cs.drop(columns="sqft").to_csv(OUT / "f1_county_share.csv", index=False)
    dn.to_csv(OUT / "f1_donut.csv", index=False)

    log.info("wrote dw1_state_counts.csv (%d rows), f1_county_share.csv (%d rows), f1_donut.csv (3 rows)",
             len(sc), len(cs))
    log.info("total facilities=%d, building area=%.3f km2", sc["facilities"].sum(), sc["building_area_km2"].sum())
    log.info("top 10 counties by building footprint area:\n%s",
             cs.head(10)[["rank", "county", "state", "building_area_m2", "share_pct"]].to_string(index=False))
    log.info("donut:\n%s", dn[["slice", "counties", "share_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
