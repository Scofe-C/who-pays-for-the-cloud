# DATA_SOURCES.md

Status labels: [Verified] checked against source · [Assumption] inference, verify on first use · [Unknown] not yet checked.

## A. Automated datasets (scripts fetch these)

### 1. Census — Value of Construction Put in Place (P2)
- URL: https://www.census.gov/construction/c30/xlsx/privsatime.xlsx  [Verified]
- Release check: https://www.census.gov/construction/c30/pdf/release.pdf
- Rows needed: "Data center" and "General office" (seasonally adjusted annual rate, $ millions). Series starts 2014-01; use 2018-01 onward.
- Caveats: nominal dollars; excludes racks and servers; recent months are revised each release — record download date.
- License: U.S. government work [Assumption].

### 2. EIA — retail sales and price by state (P1)
- API v2 route `electricity/retail-sales` [Assumption: confirm route and facet names on first call].
- Key: free, register at https://www.eia.gov/opendata/register.php. Read from `.env` `EIA_API_KEY`.
- Pull: 50 states + DC, sectors residential and all, annual, 2019–2024 (2025 optional if final annual exists [Unknown]).

### 3. BLS — CPI-U, U.S. city average, all items (P1 deflator)
- Series ID CUUR0000SA0, annual average. Public API, no key for small requests [Assumption: verify].
- Base: convert prices to 2024 dollars. Document formula in cleaning_log.

### 4. SEC EDGAR — company facts (F2)
- Endpoint pattern: `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` (10-digit, zero-padded).
- No key. Requires header `User-Agent` = `.env` `SEC_USER_AGENT`; max 10 requests/second.  [Verified]
- CIK lookup: https://www.sec.gov/files/company_tickers.json  [Verified]
- Companies: Microsoft, Alphabet, Amazon, Meta, Oracle. CIKs from memory (verify via lookup): 789019, 1652044, 1018724, 1326801, 1341439  [Assumption]
- Concept: purchases of property and equipment. Tag may differ by company and change over time — see DATA_PIPELINE.md.
- No human cross-check file. Validation is automatic (see DATA_PIPELINE.md Task 4).

## B. Manually downloaded datasets (human puts files in data/raw/)

### 5. PNNL IM3 Open Source Data Center Atlas (DW1, F1)
- Download: https://im3.pnnl.gov/datacenter-atlas — both CSV and GeoPackage  [Verified]
- Citation/DOI page: https://www.osti.gov/biblio/2550666
- Layers: point, building, campus. Campus and building polygons overlap → use BUILDING layer only for area.
- Area: if CSV has no area field, compute from GeoPackage in an equal-area CRS (EPSG:5070). Never compute area in lat/lon.
- License: ODbL 1.0. Attribution "© OpenStreetMap contributors". Published derived data must also be ODbL.
- Caveat: OSM coverage is incomplete. Titles say "mapped" data centers.

### 6. EPRI state table (DW2)
- EPRI 2024: https://restservice.epri.com/publicdownload/000000003002028905/0/Product (PDF; 2023 state values)  [Verified]
- EPRI 2026: https://powering-intelligence.epri.com/ — Figure ES-3 has 2021/2024/2030 state shares; downloadable? [Unknown]
- Check: Virginia 2023 = 33,851,122 MWh, 25.59%.

## C. Report figures → data/manual/facts.csv

Claude Code drafts this file (DATA_PIPELINE.md Task 7); the human only verifies.

### Columns
| Column | Filled by | Meaning | Example |
|---|---|---|---|
| id | Claude Code | stable key from the checklist below | pjm_2829_price |
| value | Claude Code | number exactly as printed, no units | 325.00 |
| unit | Claude Code | unit as printed | USD/MW-day |
| metric | Claude Code | what the number measures | PJM RTO capacity clearing price |
| period | Claude Code | year / delivery year / fiscal year it refers to | 2028/29 |
| source_title | Claude Code | document title | PJM 2028/2029 Base Residual Auction Report |
| source_url | Claude Code | URL from the table below | https://www.pjm.com/... |
| page | Claude Code | PDF page number (as printed) or "web" | 4 |
| evidence | Claude Code | the source sentence or table cell, ≤ 25 words, copied verbatim | (copied text) |
| as_of | Claude Code | date the source was accessed, YYYY-MM-DD | 2026-11-08 |
| expected | Claude Code | value from the checklist; flag if it differs from `value` | 325.00 |
| verified_by | HUMAN | initials after opening the page and seeing the number | ZC |
| notes | either | caveats (self-reported, secondary, at cap…) | cleared at the price cap |

Rule: a row with empty `verified_by` must not reach any chart. `validate_facts.py` fails on it.

### Sources
| prefix | Source | URL |
|---|---|---|
| lbnl24 | LBNL 2024 report | https://eta-publications.lbl.gov/sites/default/files/2024-12/lbnl-2024-united-states-data-center-energy-usage-report_1.pdf |
| lbnl25 | LBNL 2025 Update | https://escholarship.org/content/qt33m6w3x0/qt33m6w3x0.pdf |
| epri24 | EPRI 2024 | https://restservice.epri.com/publicdownload/000000003002028905/0/Product |
| epri26 | EPRI 2026 | https://powering-intelligence.epri.com/ |
| iea25 | IEA Energy and AI (2025) | https://www.iea.org/reports/energy-and-ai/executive-summary |
| iea26 | IEA Key Questions on Energy and AI (2026) | https://www.iea.org/reports/key-questions-on-energy-and-ai/executive-summary |
| pjm | PJM 2028/29 BRA report | https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2028-2029/2028-2029-bra-results-report.pdf |
| ieefa | IEEFA, July 30 2025 | https://ieefa.org/resources/projected-data-center-growth-spurs-pjm-capacity-prices-factor-10 |
| imm | Monitoring Analytics, July 2026 | https://www.monitoringanalytics.com/reports/Presentations/2026/IMM_MC_Market_Monitor_Report_20260728.pdf |
| jlarc | JLARC Report 598 | https://jlarc.virginia.gov/pdfs/reports/Rpt598-2.pdf |
| vatax | Va. Tax RD40, Jan 2 2026 | https://rga.lis.virginia.gov/Published/2026/RD40/PDF |
| vabudget | Williams Mullen summary of HB 30 (find primary budget text if possible) | https://www.williamsmullen.com/insights/news/legal-news/virginia-budget-creates-new-electricity-consumption-tax-data-centers |
| mdopc | Maryland Office of People's Counsel | https://content.govdelivery.com/accounts/MDOPC/bulletins/3ead2f8 |
| peco | PhillyVoice (look for PECO primary) | https://www.phillyvoice.com/peco-bill-increase-supply-costs/ |
| dcw | Data Center Watch | https://www.datacenterwatch.org/report |
| scc | Virginia SCC news release | https://www.scc.virginia.gov/about-the-scc/newsreleases/release/scc-issues-order-on-dev-biennial-review-2025/scc-rules-in-dev-biennial-review-case.html |

### Checklist (id → expected value)
If the document shows a different value, record the document's value, keep `expected`, and flag it in the run report.
If a value is not found in that document, leave the row out and list it as missing — never fill it from elsewhere.

| id | expected | unit / note |
|---|---|---|
| lbnl24_2014_twh | 58 | TWh |
| lbnl24_2023_twh | 176 | TWh |
| lbnl24_2023_share | 4.4 | % of U.S. electricity |
| lbnl24_2028_low / _high | 6.7 / 12 | % |
| lbnl25_2024_twh | 192 | TWh (so far only secondary sources) |
| lbnl25_2024_share | 4.7 | % |
| lbnl25_2030_mid / _low / _high | 11.8 / 9.5 / 15.3 | % |
| lbnl25_2030_twh_low / _high | 521 / 843 | TWh |
| epri24_2030_low / _high | 4.6 / 9.1 | % |
| epri24_15states_share | 80 | % of 2023 load |
| epri24_va_mwh / epri24_va_share | 33,851,122 / 25.59 | MWh / % (2023) |
| epri26_2030_low / _high | 9 / 17 | % |
| epri26_va_2030_low / _high | 39 / 57 | % |
| iea25_2024_twh | 415 | TWh, global |
| iea25_us_share_2024 | 45 | % of global |
| iea26_2025_twh / iea26_2030_twh | 485 / 950 | TWh, global |
| iea26_2025_growth | 17 | % |
| pjm_2425 … pjm_2829 | 28.92 / 269.92 / 329.17 / 333.44 / 325.00 | USD/MW-day (2425–2627 may come from ieefa) |
| pjm_2829_uncapped | 554.72 | USD/MW-day, simulated |
| pjm_2829_shortfall | 6,831 | MW |
| imm_4auction_dc / _total | 29.4 / 63.6 | USD billion |
| imm_4auction_share | 46.2 | % |
| imm_2829_dc / _total | 6.3 / 16.4 | USD billion |
| jlarc_jobs_total / jlarc_jobs_construction | 74,000 / 59,000 | jobs per year incl. indirect + induced |
| jlarc_fy23_exemption | 928.6 | USD million, self-reported, state+local+regional |
| jlarc_return_per_dollar | 0.48 | USD state revenue per USD exempted |
| vatax_fy24 / vatax_fy25 | 1,292,457,000 / 1,941,390,000 | USD, reported tax benefit (p.3) |
| vabudget_rate / vabudget_cap | 0.011 / 600 | USD per kWh / USD million per year |
| ieefa_wmd / ieefa_oh | 18 / 16 | USD per month, capacity-price effect |
| ieefa_dc_capacity / ieefa_dc_total | 10 / 21 | USD per month |
| mdopc_bge_cumulative / mdopc_bge_latest / mdopc_bge_net / mdopc_pepco_net | 16.49 / 0.83 / −3.36 / 2.50 | USD per month |
| peco_2026_usd / peco_2026_pct | 4.94 / 3.1 | USD per month / % |
| dcw_blocked_delayed | 64 | USD billion |
| scc_gs5_threshold / scc_gs5_effective | 25 / 2027-01-01 | MW / date |