# DATA_PIPELINE.md

Run tasks in order. Each task ends with its acceptance check; if a check fails, stop and report — do not work around it.
Log every step (source, download date, transformation, rows in/out, known limits) in `notes/cleaning_log.md`.

## Task 1 — Repo setup
- Create folders from CLAUDE.md, `.gitignore` (`.env`, `.venv/`, `__pycache__/`), `.env.example` with empty keys.
- `scripts/check_secrets.py`: scan all tracked/staged files for the values in `.env`; exit non-zero on a match.
- Accept: planting a fake key in a tracked file makes the check fail.

## Task 2 — Census → `data/clean/p2_construction.csv`
- Columns: `month` (YYYY-MM), `series` (data_center | general_office), `value_musd_saar`.
- Range 2018-01 to latest available month. Record the file's release vintage.
- Accept: two series, no missing months, latest month matches the current release PDF.

## Task 3 — EIA + CPI → `data/clean/p1_state_price_growth.csv`
- Columns: `state`, `pjm` (full | partial | no), `sales_2019_mwh`, `sales_2024_mwh`, `sales_change_pct`,
  `price_real_2019_cents`, `price_real_2024_cents`, `price_change_pct` (sector = all; repeat for residential in a second file).
- Real prices in 2024 dollars using CPI-U annual averages.
- PJM membership: verify against pjm.com before coding. From memory [Assumption]: full = DE, MD, NJ, OH, PA, VA, WV, DC; partial = IL, IN, KY, MI, NC, TN.
- Accept: 51 rows; no nulls; formula written in cleaning_log.

## Task 4 — SEC → `data/clean/f2_capex_long.csv` and `f2_capex_race_wide.csv`
Rules (each is a cleaning step to log):
1. Try candidate tags per company in order; log which tag supplied which periods. Tags may change across years.
2. 10-Q cash-flow values are YEAR-TO-DATE. Convert to single quarters: Q1 = 3M; Q2 = 6M − 3M; Q3 = 9M − 6M; Q4 = FY − 9M.
3. The same period appears in several filings: keep the most recently filed value.
4. Map fiscal quarters to calendar quarters by period END date (Microsoft FY ends June, Oracle May).
5. TTM = sum of 4 consecutive calendar quarters; leave blank if any quarter is missing.
- Long columns: `company`, `cal_quarter` (e.g. 2024Q3), `capex_q_usd`, `capex_ttm_usd`, `tag`, `filed`.
- Wide (Flourish bar chart race format): one row per company, one column per quarter, values = TTM in $B.
- Range: 2018Q1 to latest filed quarter.
- Accept (all automatic):
  - no negative quarterly value;
  - for every fiscal year, the 4 derived quarters sum to the annual 10-K value within 0.5% (catches YTD-differencing and tag errors);
  - print a summary table: company, fiscal year, annual value, filing URL — so the human can spot-check one if they want.

## Task 5 — IM3 → `dw1_state_counts.csv`, `f1_county_share.csv`
- Input: human-downloaded CSV + GeoPackage in `data/raw/`.
- Deduplicate by facility ID; log count removed.
- Area: BUILDING layer only (campus polygons overlap buildings). If the CSV lacks an area field, STOP and ask before adding geopandas; area must be computed in EPSG:5070.
- `dw1_state_counts.csv`: `state`, `facilities`, `building_area_km2`.
- `f1_county_share.csv`: `county_fips`, `county`, `state`, `building_area_m2`, `share_pct`, `rank`; plus a 3-row summary file for the donut: Loudoun / next 4 / all other.
- Add `data/clean/LICENSE-ODbL.txt` and an attribution column.
- Accept: 51 state rows; shares sum to 100 ± 0.1; report the actual top-5 share BEFORE anyone writes the F1 title.

## Task 6 — EPRI → `dw2_state_share.csv`
- Parse the 2024 PDF state table with pdfplumber. Columns: `state`, `dc_mwh_2023`, `share_pct_2023`.
- Accept: 51 rows; Virginia = 33,851,122 MWh and 25.59%; total within 0.5% of the report total. Otherwise stop — human will hand-enter.

## Task 7 — Draft `facts.csv` (Claude Code), verify (human)
- `scripts/draft_facts.py`: download each source in DATA_SOURCES.md §C into `data/raw/reports/`, locate each checklist id,
  fill every column except `verified_by`. `evidence` = the exact source text (≤ 25 words). `page` = page where it appears.
- Never take a value from a different document than the one listed for that id. Not found → leave out and report.
- Output a run report: rows found, rows missing, rows where `value` ≠ `expected`.
- Human then opens each `source_url` at `page`, checks `value`, writes initials in `verified_by`.
- `scripts/validate_facts.py`: every row has all columns filled including `verified_by`; `value` parses as a number (dates excepted).
- Accept: validate exits 0 only after the human has verified every row.

## Task 8 — Manual-figure CSVs for Datawrapper/Flourish
Build from `facts.csv` only (no typed numbers in code): `h1_pjm.csv`, `h2_va_tax.csv`, `h3_forecasts.csv`, `p3_iea.csv`,
`f3_jobs.csv`, `f4_imm.csv`, `dw3_bills.csv`, `dw4_ledger.csv`.
- Accept: each value in these files matches a `facts.csv` id; the id is kept as a column.