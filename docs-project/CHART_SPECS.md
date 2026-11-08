# CHART_SPECS.md

Applies to P1–P3 (Plotly) and H1–H3 (HTML). Datawrapper/Flourish styling notes are at the end for the human.

## Design tokens
| Role | Hex |
|---|---|
| Background | #F7F5F0 |
| Text | #1F1F1F |
| Secondary text | #5E5E5E |
| Gridlines | #D9D6CF |
| Costs / who pays | #B3452C |
| Gains / who wins | #2F5D50 |
| Baseline, neutral series | #3C5A78 |
| Price caps, forecasts (lines only) | #C99A2E — text in this role uses #7A5C14 |
| De-emphasized data | #BFB8AC |

Fonts (Google Fonts): Source Serif 4 (titles), Source Sans 3 (body, labels), IBM Plex Mono (numbers, sources).
Fallbacks: Georgia / Arial / Courier New.

## Rules for every chart page
- Standalone file `docs/charts/<id>.html`; data inlined as JSON; works when opened locally.
- Title = the conclusion sentence; subtitle; chart; source line with snapshot date.
- Units in axis titles. Never mix $/MW-day, ¢/kWh, $/month on one axis.
- Tooltips written as HTML (`hovertemplate` in Plotly; HTML strings in custom charts).
- Usable at 380px width: no horizontal page scroll; wide content scrolls in its own container.
- Controls are real `<button>`/`<input>`/`<select>` with labels; targets ≥ 44px; visible focus.
- `@media (prefers-reduced-motion: reduce)` disables animation.
- `aria-label` on each SVG summarizing what it shows.
- Plotly: `write_html(include_plotlyjs="cdn")`, responsive config; then inject the Google Fonts `<link>` into `<head>`.
- Custom HTML: vanilla JS + SVG, no libraries.

## P1 — State scatter (Plotly)
x = sales change 2019–2024 (%), y = real price change (%). One dot per state + DC.
Dropdown to highlight: PJM states / none. Hover: state, both values, PJM status. Dashed OLS trend line, labeled.
Title: "Growth alone didn’t raise prices" (only if the trend is negative in our data — check first).

## P2 — Construction line (Plotly)
Two lines, monthly 2018-01 → latest; range slider. Data centers in #B3452C, general office in #3C5A78.
Hover: month, value ($B SAAR). Note under chart: nominal, excludes servers.

## P3 — IEA global demand (Plotly)
Horizontal bars 2023, 2024, 2025, 2030 (projection hatched or lighter). Grow-in animation on load.
Note which IEA report each value comes from.

## H1 — PJM auctions (HTML)
Columns per delivery year 2024/25 → 2028/29 ($/MW-day). Dashed #C99A2E cap marker on years that cleared at the cap.
Hollow circle at $554.72 for 2028/29 "without the cap". Year buttons; selected year shows a one-sentence note below.

## H2 — Virginia tax (HTML)
Bars FY2023–FY2025 ($B, self-reported, state + local). Toggle button overlays the $0.6B/yr cap of the new 1.1¢/kWh tax.
Line under chart: JLARC — about 48¢ of state revenue per $1 of exemption.

## H3 — Forecast fan (HTML)
y = share of U.S. electricity (%). Actual dots: 4.4% (2023), 4.7% (2024). Range bars at target years:
LBNL 2024 → 2028 6.7–12; EPRI 2024 → 2030 4.6–9.1; LBNL 2025 → 2030 9.5–15.3; EPRI 2026 → 2030 9–17.
Toggle buttons per report. Annotation: 2024 actual landed at the low end of the 2024 report's path.

## Notes for the human (Datawrapper / Flourish)
- Use the same hex values; record the fonts each tool actually used.
- DW1: USA hexagon map. DW2: USA » States choropleth, bins <5 / 5–10 / 10–20 / 20%+.
- F1: donut, 3 slices only. F2: Bar chart race template, values = TTM capex $B, label "includes non-data-center capex".
- F4: stacked bars. DW3: grouped bars, 2025 jump vs 2026 increment. DW4: searchable table.
