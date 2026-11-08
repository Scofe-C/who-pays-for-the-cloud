# Cleaning log

## Task 5 — IM3 Data Center Atlas → DW1, F1  (run 2026-11-07, `scripts/clean_im3.py`)

**Source**: PNNL IM3 Open Source Data Center Atlas, version v2026.02.09 (from filename).
https://im3.pnnl.gov/datacenter-atlas · citation https://www.osti.gov/biblio/2550666 · ODbL 1.0, © OpenStreetMap contributors.
**Download date**: 2026-11-07 [Assumption: file mtime in `data/raw/`; human placed files, actual download date not recorded].
**Raw files** (unmodified): `im3_open_source_data_center_atlas_v2026.02.09.csv` (1,479 rows), `.gpkg` (layers point 105 / building 1,239 / campus 135, EPSG:4326).

### Steps
| # | Step | Rows in → out |
|---|---|---|
| 1 | Load CSV; `county_fips` = `state_id` (2) + `county_id` (3), kept as string | 1,479 |
| 2 | Drop Puerto Rico (outside 50 states + DC) | 1,479 → 1,477 |
| 3 | Dedupe by `id` | 1,477 → 1,472 (5 removed) |
| 4 | State aggregation; add 0-rows for states with no records | 46 → 51 states |
| 5 | County aggregation, BUILDING type only | 1,236 buildings (after PR drop + dedupe) → 205 counties |

### Decisions
- **Area field.** CSV has `sqft`, so no geopandas. Validation: recomputed each building polygon's area from the GeoPackage WKB with a local equal-area (equirectangular, per-polygon latitude) approximation. Ratio computed/`sqft` = 0.997–1.003 (mean 0.9991) over 1,239 buildings. This was **not** an EPSG:5070 computation; it only shows `sqft` is the footprint area. Conversions: m² = sqft × 0.09290304; km² = m² / 1e6.
- **Duplicates.** All 5 duplicate ids are one feature listed once per county it straddles (same state, same sqft): 3 campuses (Project Osmium IA, Google OH, Meta Kansas City MO) and 2 buildings (Digital Realty ATL11 GA, Google NBY-6 OH). Rule: keep the row with the lowest `county_fips` (deterministic). Sensitivity check with the highest instead: top-5 counties unchanged; top-5 share 31.37% vs 31.52%. State counts are unaffected.
- **`facilities`** = unique ids across all three types (point + building + campus). Campus polygons can contain mapped buildings, so a campus and its buildings are both counted. Breakdown columns `n_point`, `n_building`, `n_campus` are included so the chart can use another definition.
- **Zero states.** AK, DE, HI, RI, VT have no atlas records → `facilities = 0`, area 0. This means "none mapped in OSM/IM3", not a confirmed zero.
- **Area denominator** (F1) = all building FOOTPRINT area (2-D polygon, not multi-storey floor space) in 50 states + DC (17.750 km²). Campus polygons excluded (they overlap buildings); points have no area.
- **Shares** are rounded to 4 dp in `f1_county_share.csv` and 2 dp in `f1_donut.csv`; both sum to 100 ± 0.1 (checked).

### Acceptance
- 51 state rows ✔ · county shares sum to 100 ± 0.1 ✔ · donut sums to 100 ± 0.1 ✔ · no nulls ✔ · FIPS 5-digit ✔ · Loudoun is rank 1 ✔
- **Top-5 share = 31.37%** of mapped building footprint area (Loudoun 14.77%, Prince William 5.02, Maricopa 4.98, Licking 3.64, Polk 2.96).

### Outputs
`data/clean/dw1_state_counts.csv`, `f1_county_share.csv`, `f1_donut.csv`, `LICENSE-ODbL.txt` (official text fetched 2026-11-07 from opendatacommons.org).

### Known limits
OSM coverage is incomplete and uneven; all figures are "mapped" data centers / mapped footprint area. Footprint area ≠ floor area for multi-storey buildings.

## Tasks 2–4 — downloads (run 2026-11-07, `scripts/fetch_*.py`)

Raw files are write-once (`fetch_common.write_once` never overwrites); filename carries the download date.

| Script | File | Source | Notes |
|---|---|---|---|
| fetch_census.py | `census/census_c30_privsatime_2026-11-07.xlsx` | census.gov C30 privsatime.xlsx | Last-Modified 2026-11-02 15:00 GMT. Sheet "Private SA", SAAR $M; wide layout, `Office > General` and `Data center` are columns. |
| fetch_census.py | `census/census_c30_release_2026-11-07.pdf` | C30 release.pdf | Same release (Last-Modified 2026-11-02); used for the latest-month check. |
| fetch_eia.py | `eia/eia_retail_sales_annual_2026-11-07.json` | EIA API v2 `electricity/retail-sales/data`, annual, sectorid ALL+RES, 2019–2025 | 868 rows = 62 ids × 7 yr × 2 sectors. 62 ids = 50 states + DC + US + 10 Census-division aggregates (to drop). Units: sales million kWh (×1000 → MWh), price cents/kWh, nominal. Route/facets confirmed via API metadata. API key not echoed in response (checked). |
| fetch_cpi.py | `bls/bls_CUUR0000SA0_monthly_2026-11-07.json` | BLS public API v1 (keyless), CUUR0000SA0, 2018–2025 | v1 returns monthly only, **no M13 annual average**. 2025-10 = "-" (BLS footnote: unavailable due to 2025 lapse in appropriations). BLS flat file download.bls.gov returned 403 to a generic client. |
| fetch_sec.py | `sec/sec_company_tickers_2026-11-07.json` + 5 × `sec_companyfacts_<TICKER>_CIK##########_2026-11-07.json` | data.sec.gov companyfacts | CIKs resolved by ticker; all 5 match DATA_SOURCES. UA from `.env`. ~19.5 MB total. |

### Findings that affect cleaning (not yet resolved)
- **CPI annual average (Task 3).** Options: (a) mean of 12 monthly values (2019, 2024 complete); (b) register a BLS v2 key for published M13 averages. Undecided.
- **Amazon capex tag (Task 4).** `PaymentsToAcquirePropertyPlantAndEquipment` ends 2017-03-31; Amazon uses `PaymentsToAcquireProductiveAssets` (2016-12-31 → 2026-09-30). Note Amazon's line is net of proceeds/incentives? [Unknown: check 10-K line label]. Others: GOOGL/META/MSFT to 2026-09-30, ORCL to 2026-08-31 on the PP&E tag.

## Task 2 — Census → `p2_construction.csv`  (run 2026-11-07, `scripts/clean_census.py`)
- **Input**: `census/census_c30_privsatime_2026-11-07.xlsx`, sheet "Private SA". **Release vintage: November 2, 2026** (Release CB26-176, data through September 2026; next release December 1, 2026).
- Series: column `Office > General` → `general_office`; column `Data center` → `data_center`. Private construction, SAAR, nominal $ millions. Census "Office" total (145,633 in Sep-2026) **includes** data centers and financial; the comparison series is "General" office only.
- Dates `Mon-YY[p|r]` → `YYYY-MM`; two-digit years ≥ 90 = 19xx. `p`/`r` flags kept in `status` (preliminary / revised).
- Rows: 105 months (2018-01 … 2026-09) × 2 series = 210. No missing months.
- Acceptance ✔: 2 series, no gaps; latest month = PDF release month (September 2026); private Office Sep-2026 = 145,633 in both xlsx and release PDF p.3 (the PDF does not break out data centers, so Office is the tie-out).
- Data center first exceeds general office in **2025-04**. Sep-2026: data center 96,462 vs general office 45,964.

## Task 3 — EIA + CPI → `p1_state_price_growth.csv`, `p1_state_price_growth_residential.csv`  (run 2026-11-07, `scripts/clean_eia.py`)
- **Input**: `eia/eia_retail_sales_annual_2026-11-07.json` (sectors ALL, RES), `bls/bls_CUUR0000SA0_monthly_2026-11-07.json`.
- Kept 50 states + DC (dropped US and 10 division aggregates); years 2019 and 2024 only (2025 in raw, unused). Values cast from strings; any non-numeric fails.
- Units: sales million kWh × 1000 → MWh. Price cents/kWh.
- **CPI annual average = mean of the 12 monthly values** (user decision 2026-11-07; BLS v1 has no published M13). Both years have 12 numeric months.
  - CPI_2019 = 255.6574, CPI_2024 = 313.6888, deflator = 1.226989.
- **Formula**:
  - `price_real_2019_cents = price_nominal_2019 × CPI_2024 / CPI_2019`
  - `price_real_2024_cents = price_nominal_2024`
  - `price_change_pct = (price_real_2024 / price_real_2019 − 1) × 100`
  - `sales_change_pct = (sales_2024_mwh / sales_2019_mwh − 1) × 100`
- Extra columns beyond spec: `price_nominal_2019_cents`, `sector`, `source`.
- **PJM column**: membership (14 jurisdictions) [Verified: pjm.com territory-served page, 2026-11-07, "all or parts of …"]. **Full vs partial split is [Assumption]** carried from DATA_PIPELINE.md — pjm.com does not state it. Human must confirm before P1 colours by `pjm`.
- Acceptance ✔: 51 rows per file, no nulls. Spot check: VA all-sector 2024 sales 138,044,772 MWh = API value 138,044.772 million kWh.

## Task 4 — SEC → `f2_capex_long.csv`, `f2_capex_race_wide.csv`  (run 2026-11-07, `scripts/clean_sec.py`)
- **Input**: 5 × `sec/sec_companyfacts_*_2026-11-07.json`. Forms kept: 10-K, 10-Q, /A. (Drops MSFT 8-K facts.)
- Periods identified by start/end dates (not filing fy/fp). FY = 12M fact ending in FYE month (Dec; MSFT Jun; ORCL May). Current partial FY start = last FY end + 1 day.
- **Rule 1 — tags** (candidate order `PaymentsToAcquirePropertyPlantAndEquipment`, `PaymentsToAcquireProductiveAssets`; one tag per FY, chosen as the first carrying that FY's 12M fact, else its 3M fact):
  - Microsoft, Alphabet, Meta, Oracle: PaymentsToAcquirePropertyPlantAndEquipment for all quarters 2017Q2–2026Q3.
  - Amazon: PaymentsToAcquireProductiveAssets 2017Q4–2026Q3. Amazon has no 6M fact ending 2017-06-30 under either gross tag, so 2017Q2–Q3 cannot be derived → **TTM blank 2018Q1, 2018Q2**. The only 6M-2017 value is under `PaymentsForProceedsFromProductiveAssets` (a net-of-proceeds concept, 4,362 vs 5,261 $M in two filings) — not used, to avoid mixing net and gross.
- **Rule 2** YTD differencing; **Rule 3** keep most recently filed per (tag, start, end); **Rule 4** calendar quarter from period end (ORCL Feb-28 → Q1, May-31 → Q2, Aug-31 → Q3, Nov-30 → Q4); **Rule 5** TTM blank unless 4 consecutive quarters.
- Rows: 175 long (5 companies × 35 quarters, 2018Q1–2026Q3); wide 5 × 35, TTM in $B (3 dp).
- **Checks**
  - No negative quarter ✔.
  - Spec check (4 quarters = 10-K annual ± 0.5%) ✔ — note this is an identity by construction (Q4 = FY − 9M), so it cannot fail.
  - Derived quarters vs separately filed discrete 3M facts, 2017Q2+: MSFT 18, GOOGL 8, AMZN 18 compared, 0 off by > 0.5% ✔. META and ORCL file no discrete 3M facts (0 compared).
  - Amazon computed TTM vs Amazon-reported trailing-12M facts: 25 compared, 0 off by > 0.5% ✔.
  - Outside scope: one GOOGL 2015Q3 restated comparative differs ~1% from the YTD-derived value; checks are scoped to 2017Q2+.
- **Amazon gross vs net — resolved** [Verified: Amazon 10-K FY2025, https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm, cash-flow statement, checked 2026-11-07]: "Purchases of property and equipment (52,729) (82,999) (131,819)" is a GROSS line; "Proceeds from property and equipment sales and incentives" is reported separately. Matches FY2023–2025 values in f2 exactly.
- Latest TTM (2026Q3, $B): Amazon 215.2, Alphabet 159.8, Microsoft 135.9, Meta 104.4, Oracle 75.7. Capex includes non-data-center assets.

## Report downloads (run 2026-11-07, `scripts/fetch_reports.py`)
- 13 of 16 sources saved to `data/raw/reports/<prefix>_2026-11-07.{pdf,html}` with an honest generic client.
- **Blocked (HTTP 403)**: lbnl25 (escholarship.org), iea25, iea26 (iea.org). Human must download manually into `data/raw/reports/` as `<prefix>_<YYYY-MM-DD>.pdf|html`, then re-run `draft_facts.py`.
- **epri26**: powering-intelligence.epri.com returns a 1.9 KB JavaScript app shell with no text; needs a human-downloaded PDF/figure.
- scc (Virginia SCC release) downloaded but has no checklist ids.

## Task 6 — EPRI 2024 → `dw2_state_share.csv`  (run 2026-11-07, `scripts/clean_epri.py`)
- Parsed Appendix A table (PDF pages 28–29) with pdfplumber line regex: state, 2023 MWh, 2023 %EC (+ 4 scenario pairs, discarded).
- **44 states parsed** — the report covers 44 states only (its own text: "a table showing 44 states"). Not in the report: **AK, AR, DE, DC, MS, VT, WV** → kept as rows with BLANK values, `in_epri_table = False`. Never 0, never estimated.
- Virginia check ✔ 33,851,122 MWh, 25.59%.
- **Spec deviation**: acceptance asks for 51 populated rows and "total within 0.5% of report total". The report states no 2023 national total, so that check cannot be run. Substitute consistency check: top-15 states = 83.3% of the 44-state sum (152,120,846 MWh); report says "fifteen states account for 80%" of national load — consistent (the 44-state sum is ≤ national).
- DW2 bins (<5 / 5–10 / 10–20 / 20%+): 32 / 6 / 5 / 1.

## Task 7 — `data/manual/facts.csv` draft  (run 2026-11-07, `scripts/draft_facts.py`, `scripts/validate_facts.py`)
- Each id is searched ONLY in its listed document with a context-anchored regex whose value group is a generic number. Evidence = ≤ 25 words of extracted text around the match.
- `page` = PDF viewer page (1-based); `source_url` carries `#page=N`. Printed page numbers differ (e.g. LBNL p.6 is printed "5"). Deviation from "page as printed", chosen so the link opens on the right page.
- Results: **41 rows found, 17 missing, 3 value ≠ expected**. Details in `notes/facts_run_report.md`.
  - Missing: 7 × lbnl25, 5 × iea25/iea26 (403), 4 × epri26 (no text), `imm_4auction_total` (IMM states $29.4B = 46.2% but never states the four-auction total).
  - Mismatch: `lbnl24_2014_twh` doc "about 60 TWh" (2014–2016) vs 58; `pjm_2829_shortfall` 6,831.3 vs 6,831; `jlarc_return_per_dollar` printed "48¢" vs 0.48 (unit only).
- Extra row (not in checklist): `jlarc_jobs_operations` = 15,000 (JLARC p.33 table), for the F3 waffle.
- `vatax_fy24/25` taken from RD40 Table 2 (PDF p.4); the p.3 table text extracts garbled ("11292,457 ,000").
- `ieefa_dc_*`: "dc" = Washington D.C. (Pepco), not data centers.
- `validate_facts.py`: 0 structural errors; exits 1 until every row has `verified_by` (by design).

## Task 7 update: manually downloaded reports (2026-11-07)

- The human downloaded the four sources that blocked scripted access into `data/raw/energy_report/`, keeping the original filenames:
  - `lbnl25`: `qt33m6w3x0.pdf`
  - `epri26`: `3002034696_Powering Intelligence 2026_ ... .PDF`
  - `iea25`: `EnergyandAI.pdf` (full report)
  - `iea26`: `KeyQuestionsonEnergyandAI.pdf` (full report)
- `draft_facts.py` reads them in place; they are never renamed or copied.
  - `as_of` is the file modification date, because the filenames carry no date.
  - A manual file takes precedence over a scripted stub, such as the epri26 JavaScript shell in `data/raw/reports/`.
- `source_url`:
  - lbnl25: the URL is the PDF itself, so it gets `#page=N`.
  - iea25, iea26, epri26: the URLs are landing pages, so there is no `#page`. `page` is the PDF page of the local file, as stated in `notes`.
- Result: 57 rows, 1 missing (`imm_4auction_total`, not stated in the IMM report), and 3 mismatches flagged as before.
- `iea26_2030_twh`: the text value is 950 ("roughly doubling from 485 TWh in 2025 to 950 TWh in 2030", p10). Annex Table A.4 Base Case shows 945. The text value is kept and the table value is noted.

## facts.csv encoding repair (2026-11-07)

- The human verified all 57 rows (`verified_by` = ZC/zc), but saving from Excel re-encoded the file as Windows-1252. That damaged 14 evidence strings and 1 note (`–`, `’` and `¢` became mojibake), rewrote `as_of` as 2026/11/7, and dropped trailing zeros (12.0, 325.00, 2.50).
- Repair: the committed UTF-8 file was restored and only the human's `verified_by` values were carried over. No figure changed.
- Hazard: re-running `draft_facts.py` rewrites facts.csv with `verified_by` empty. Do not re-run it without first preserving verifications.

## Task 8: chart CSVs from facts.csv (`scripts/build_manual_csvs.py`)

- Rules:
  - Every value comes from a verified facts.csv row, and the id is kept in `fact_id`.
  - A value computed from two facts lists all its ids joined by `+`, plus a `derivation` text.
  - Unverified rows stop the build, and so does a file that is not UTF-8.
- Outputs:
  - **h1_pjm**: 5 delivery years. `at_cap` = True only where the PJM report states it (2027/28, 2028/29). It is blank for 2026/27 because the report says only that the cap was "in effect" that year. The uncapped simulation ($554.72) applies to 2028/29 only.
  - **h2_va_tax**:
    - FY2023 comes from JLARC; FY2024 and FY2025 come from Va. Tax RD40. All are self-reported, converted to USD billion.
    - It also has the new-tax cap, the tax rate and the 48¢ return.
  - **h3_forecasts**:
    - Actual values: 4.4% (2023) and 4.7% (2024). Plus four report ranges; LBNL 2025 also has its 11.8% Reference Case value.
    - Unit wording differs between reports (EPRI 2024 "of generation", EPRI 2026 "of demand"); the unit column keeps it.
  - **p3_iea**: 2024, 2025 and 2030. **2023 is missing**; facts.csv has no IEA 2023 value.
  - **f3_jobs**: squares = jobs / 1000. The check construction + operations = total passes (59,000 + 15,000 = 74,000).
  - **f4_imm**:
    - 2028/29: other = 16.4 − 6.3 = 10.1, and the data-center share = 38.41%.
    - Last four auctions: data center $29.4B and 46.2%, so other = 53.8%. The USD total and USD other are blank because `imm_4auction_total` is not in facts.csv.
  - **dw3_bills**:
    - BGE 2025 jump = cumulative 16.49 − latest 0.83 = 15.66 (derived).
    - The rows measure different things (IEEFA capacity-price effect, Pepco D.C. total bill, MD OPC auction effect, PECO total bill); the `measure` column says which.
  - **dw4_ledger**: 19 rows. The Wins/Pays/Context classification is an editorial draft for human review.

## IEA 2023 row and verification-preserving drafts (2026-11-07)

- `draft_facts.py` now keeps the existing `verified_by` when a row's value is unchanged. A changed value clears it and logs a warning. Re-running the script no longer wipes the human's verification.
- New row `iea26_2023_twh` = 360 TWh, from IEA Key Questions on Energy and AI (2026), Annex Table A.4, Base Case (PDF p110). It awaits human verification.
- Caveat: the same table gives 416 TWh for 2024, while P3's 2024 bar uses 415 from the IEA 2025 text.
- `build_manual_csvs.py` adds the 2023 bar to `p3_iea.csv` only after that row is verified.

## Prep for Datawrapper/Flourish import (2026-11-07)

- **F4:** new fact `imm_2829_share` = 38.2% (IMM p.4, "This was 38.2 percent"). Once it is verified, `f4_imm.csv` uses IMM's published share for 2028/29 and keeps the computed 6.3/16.4 = 38.41% in a new `notes` column. Until then it keeps the computed value and the note says so.
- **DW3:** Pepco D.C. `jump_2025` is now the capacity-price portion (10, `ieefa_dc_capacity`). The total bill increase (21, `ieefa_dc_total`) moved to the new column `total_bill_increase_usd_month`.
- **F2:** new file `f2_capex_race_wide_from2018Q3.csv` drops 2018Q1–Q2, where Amazon's TTM is blank. The original file is kept.
- **DW4:**
  - New `display` column with formatted figures. Formatting only; the value is the fact's.
  - New `dw4_ledger_short.csv`: 8 rows, one per "who", using picks agreed with the human (vatax_fy25, jlarc_jobs_construction, jlarc_return_per_dollar, imm_4auction_dc, ieefa_dc_total, ieefa_wmd, dcw_blocked_delayed, lbnl25_2030_mid).
- **DW2:** checked that the 7 states missing from the EPRI table stay empty, not 0. No change.

## Upload files for Datawrapper/Flourish reproduced by script (2026-11-07)

`scripts/build_uploads.py` builds `data/upload/*.csv` from `data/clean/` and `facts.csv`. It then compares each file to the hand-made version in `data/upload_manual/` (moved there from `data/manual/*_upload.csv`). Numbers are compared after rounding to the hand file's decimals, and strings must match exactly. Result: `notes/upload_diff_report.md`. The script exits 0 only if every difference is explained.

- **dw1** (51 rows):
  - Columns: state, state_name, facilities, building_area_km2.
  - `state_name` is joined on the state code from `dw2_state_share.csv` (EPRI table names), one-to-one. The build stops on any unmatched code.
- **dw2** (51 rows):
  - Columns: state, state_name, dc_mwh_2023 (integer), share_pct_2023.
  - The 7 states not in the EPRI table (AK, AR, DC, DE, MS, VT, WV) stay blank; the build stops on any 0.
  - There is no hand-made counterpart.
- **dw3** (6 rows):
  - Taken from `dw3_bills.csv` with the chart labels.
  - Pepco D.C. 2025 jump = 10, the capacity portion (`ieefa_dc_capacity`), not the 21 total.
  - BGE 2025 jump = 16.49 − 0.83 = 15.66, re-checked against facts.
  - Blanks stay blank.
- **dw4** (9 rows: 2 Wins, 5 Pays, 2 Context):
  - Figure strings are formatted from fact values.
  - Source is a markdown link to the fact's `source_url`, which includes `#page=` for PDFs. Page numbers come from facts.csv.
- **f1** (3 rows):
  - share_pct rounded to 1 decimal; the rounded shares sum to 100.
  - floor_area is text "x.xx km²" (m² / 1e6).
  - The "N other counties" count comes from `f1_county_share.csv` (205 − 5 = 200).
- **f2** (5 rows):
  - Trailing-4-quarter capex in $B (1 decimal) from `f2_capex_long.csv`, starting 2018Q3 (Amazon has no TTM before then).
  - Headers are "YYYY QN"; `category` = company.
- **f2_captions** (4 rows): each data caption is checked against unrounded TTM, and the build fails if a check is false.
  - (1) Amazon and Meta are lower at 2023Q4 than at their 2022–23 peak.
  - (2) Microsoft ≥ Alphabet at 2025Q1, and Alphabet > Microsoft from 2025Q2 through the latest quarter. Alphabet was also ahead in 2018Q3–2023Q1, so the caption describes it retaking the lead.
  - (3) Oracle 2026Q3 / 2024Q4 = 7.04 ≥ 7.
  - The ChatGPT caption date comes from the new facts row `openai_chatgpt_launch` (hand-entered; openai.com returns 403 to automated fetches; awaiting verification).
- **f3** (2 rows): one block, two phases; icons = jobs / 1000 (asserted).
- **f4** (2 rows):
  - Four auctions: 46.2 / 53.8. Total $63.6B = 29.4 / 0.462, derived because IMM does not state it.
  - 2028/29: 38.4 / 61.6, computed from 6.3 / 16.4. IMM p.4 states 38.2%; this is reported in the diff report, and the file is not changed.
- **Comparison result:** two differences, both explained. (a) dw2 has no hand-made file. (b) The DW4 jobs source pages: the generated file cites the facts.csv evidence pages 32 and 34; the hand-made file cites p.33, a table with all three numbers. Both are correct.
- **Other changes:**
  - `draft_facts.py` now keeps hand-entered rows (ids with no checklist pattern) when it re-runs.
  - `validate_facts.py` accepts ISO dates and true/false as values. It allows unverified rows that are listed in `PENDING_OK`, where every reader is gated on verification, and lists them as warnings.

## H1: 2026/27 price-cap status (2026-11-07)

- Primary source: PJM 2026/2027 Base Residual Auction Report, downloaded to `data/raw/reports/pjm2627_2026-11-07.pdf` (new file, added to `fetch_reports.py`). PDF p.6 (printed p.3) says: "For the 2026/2027 BRA, all prices cleared at the cap ($329.17)." The OPIS secondary source was not needed.
- New hand-entered facts row `pjm_2627_at_cap` = true. It awaits human verification.
- `build_manual_csvs.h1_pjm` sets 2026/27 `at_cap=True` (new columns `at_cap_fact_id` and `at_cap_source`) only once that row is verified. Until then the cell stays blank and a warning is logged.
- `build_charts.h1`: the title comes from the number of consecutive at-cap auctions ending with the latest. Three gives "Three auctions in a row hit the ceiling"; two keeps "The last two auctions hit the price cap". When the cap status is sourced, the source line adds the 2026/27 report and the "PJM report does not state…" note is dropped. A scratch test with a simulated verification produced the three-auction title, `atCap` [F,F,T,T,T], and no note.

## DW4 jobs source page (2026-11-07)

- Human choice: the DW4 row "Jobs supported per year" now cites JLARC PDF p.33, the table showing 59,000 / 15,000 / 74,000 jobs. The link is `#page=33` and the label is "JLARC, p. 33". It is set in `build_uploads.SOURCE_PAGE`.
- facts.csv keeps its evidence pages (32 for 74,000, 34 for 59,000); the facts rows are unchanged.
- The only remaining difference from the hand-made file is the label: the hand-made file says "pp. 33–34". Both link to p.33.
