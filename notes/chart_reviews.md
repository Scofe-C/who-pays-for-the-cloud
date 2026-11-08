# Chart review notes (human review of AI-built charts)

PROJECT_BRIEF requires a human review note for each AI-generated chart. Claude Code drafts the checklist below; the human ticks it and signs.
Build: `python scripts/build_charts.py`, output in `docs/charts/`. Preview: `python -m http.server 8000 -d docs`, then open http://localhost:8000/charts/p1.html.

## P1: State scatter (`docs/charts/p1.html`)
- [ ] Title claim holds: the build stops unless the OLS slope is below 0 (it is −0.667, r = −0.61).
- [ ] Hover a few states and check them against `data/clean/p1_state_price_growth.csv`.
- [ ] Corner counts (25 / 4 / 13 / 9) match the data; labelled states VA, ND, CA, DC.
- [ ] Highlight → "PJM states": 8 states are filled red (whole state in PJM) and 6 are open red (part of the state in PJM). **The whole/part split is our classification**: confirm it or change it.
- [ ] The outlier near +30% price change is a real data point; identify it by hovering.
- Reviewed by: ____  Date: ____

## P2: Construction line (`docs/charts/p2.html`)
- [ ] The title says "general office", not "office". The Census "Office" total includes data centers.
- [ ] Data centers stay above general office every month from September 2025. They first crossed in April 2025 but dipped back below afterwards.
- [ ] The latest month (September 2026) is preliminary, and hover shows each month's status.
- [ ] The notes say: nominal dollars, servers and racks not included.
- Reviewed by: ____  Date: ____

## P3: IEA global demand (`docs/charts/p3.html`)
- [ ] "Nearly doubles" refers to 2025 → 2030 (485 → 950 TWh). The build checks that the ratio is between 1.8 and 2.0.
- [ ] Mixed report editions: 2024 = 415 comes from IEA 2025, and the IEA 2026 table gives 416. The footnote says so. Keep it, or switch 2024 to 416 so all bars come from one table.
- [ ] The 2030 bar is hatched and labeled "projection"; the subtitle gives report year 2026.
- [ ] The bars grow in on load; with the OS "reduce motion" setting on, they appear at once.
- Reviewed by: ____  Date: ____

## H1: PJM auctions (`docs/charts/h1.html`)
- [ ] Title follows `at_cap`. 2026/27 cleared at the cap per the PJM 2026/2027 BRA Report, PDF p.6: "For the 2026/2027 BRA, all prices cleared at the cap ($329.17)." (`pjm_2627_at_cap`). Once that row is verified, the title becomes "Three auctions in a row hit the ceiling", 2026/27 gets the cap marker, and the "report does not state" note goes away. Until then the chart keeps "The last two auctions hit the price cap".
- [ ] The peak is 2027/28 at $333.44, not 2028/29 (PROJECT_BRIEF guardrail).
- [ ] Hollow circle at $554.72 = PJM simulation without the cap and floor, 2028/29 only.
- [ ] The year buttons update the one-sentence note, and every sentence is generated from the data.
- Reviewed by: ____  Date: ____

## H2: Virginia tax (`docs/charts/h2.html`)
- [ ] Labelled "self-reported, state + local". FY2023 comes from JLARC, which also includes regional tax; FY2024–25 come from RD40. The footnote says so.
- [ ] The $0.6B cap and the 1.1¢/kWh rate come from a secondary source (Williams Mullen summary of HB 30). Consider fetching the primary bill text.
- [ ] The title claim is checked at build time: FY2025 benefit $1.94B > $0.6B cap.
- Reviewed by: ____  Date: ____

## H3: Forecast fan (`docs/charts/h3.html`)
- [ ] **Deviation from CHART_SPECS:** columns are categories (actual 2023, actual 2024, then one column per report) instead of a calendar-year x-axis. Three reports target 2030 and would overlap on a time axis, especially at 380 px. Each column states its report year and target year.
- [ ] The annotation quotes LBNL 2025 p.10, "This falls at the low end of the estimated range in the 2024 Report". The build also checks 4.7% < 6.7%.
- [ ] Unit differences (consumption / generation / demand) are footnoted.
- [ ] The report toggle buttons fade each column in or out.
- Reviewed by: ____  Date: ____

## Hero: hex tile map (`docs/hero.html`)
- [ ] Tile colors use the DW1 steps (breaks 1 / 10 / 50 / 100 / 200), computed from `data/clean/dw1_state_counts.csv`. Spot-check a few states against DW1.
- [ ] Virginia (319 records) is drawn in #B3452C instead of its step color. It is the only state in the 200+ step, so the darkest blue (#1E3348) doesn't appear on the map.
- [ ] The tile positions are the standard 11 × 8 US tile grid. Odd rows are offset half a tile to make the hexagon tiling, so some neighbors shift slightly (for example, DC sits next to SC).
- [ ] No text except state abbreviations and the attribution footer. The aria-label is generated from the data (total, top 5, number of states with zero).
- [ ] With "reduce motion" on, the pulse and the Virginia ring stop.
- [ ] At 380 px the map is about 240 px tall and the labels are about 10 px. Check that this is readable on a phone, and set the Sites iframe height (≤ 420 px).
- Reviewed by: ____  Date: ____

## Checks done by Claude Code (2026-11-07)
- Rendered in headless Edge at 900 px and inside a 380 px iframe: no horizontal page scroll. Long axis titles were shortened so they don't clip at 380 px.
- P1 highlight menu tested by script: 37 grey markers, 14 red (8 filled, 6 open), and the key appears.
- Not checked: real phones, hover on touch devices, and the Google Sites embed (Phase 0 spike; iframe height still unknown).
- H1–H3 (2026-11-07): rendered at 900 px and in a 380 px iframe. A script tested H1 year buttons (note and aria-pressed), the H2 cap toggle (line appears, button text flips) and an H3 report toggle (column fades). Hover tooltips not tested on touch devices.
- Hero (2026-11-07): rendered at 900 px with reduced motion, inside 380 px and 1200 px iframes. No horizontal scroll, and the footer wraps at 380 px. The animation was not checked frame by frame.
