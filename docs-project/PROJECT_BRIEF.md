# PROJECT_BRIEF.md

## Goal
A public, interactive data story (Google Sites) answering: in the AI data-center boom, who wins and who pays?
Site copy is in English.

## Grading constraints
- Data cleaning 15 pts: at least 4 datasets, every cleaning step documented (`notes/cleaning_log.md`).
- Narrative 40, Visuals 20, Website 15, Peer review 10.
- 9–15 charts total, all interactive. Each tool (Datawrapper, Flourish, Plotly, custom HTML) needs at least 3.
- Tooltips written in HTML. Site must list hex colors and fonts used.
- AI-generated content must be human-reviewed (keep a review note per chart).

## Who builds what
- Claude Code: data pipeline, clean CSVs for all charts, Plotly charts P1–P3, HTML charts H1–H3, GitHub Pages site.
- Human (in web UIs): Datawrapper DW1–DW4, Flourish F1–F4, Google Sites pages, narrative text.

## Story structure and the 14 charts

| Act | ID | Tool | Chart | Data | Message (title) |
|---|---|---|---|---|---|
| 1 Scale | DW1 | Datawrapper | US hexagon/tile map, facility counts by state | IM3 Atlas | Mapped data centers cluster in a handful of states |
| 1 | DW2 | Datawrapper | Geographic state choropleth, share of state electricity | EPRI state table | In Virginia, one in four kWh went to data centers |
| 1 | F1 | Flourish | Donut, 3 slices: Loudoun / next 4 counties / all others | IM3 building layer, floor area by county | Five counties hold [x]% of mapped floor space (title decided after data) |
| 2 Power | H3 | HTML | Forecast fan: 2023/2024 actual + each report's range | facts.csv (LBNL 2024, LBNL 2025 Update, EPRI 2024, EPRI 2026) | Forecasts for 2030 keep rising, even as 2024 came in at the low end |
| 2 | P3 | Plotly | Bars: global data-center electricity 2023, 2024, 2025, 2030 | facts.csv (IEA 2025, IEA 2026) | Global demand nearly doubles by 2030 |
| 3 Money | P2 | Plotly | Monthly line, data centers vs general office, 2018-01 to latest | Census VIP | Data-center construction now outspends office buildings |
| 3 | F2 | Flourish | Bar chart race, 5 companies, trailing-4-quarter capex, 2018Q1 to latest | SEC EDGAR | The capex race (do NOT call it "AI spending": capex includes non-DC assets) |
| 3 | F3 | Flourish | Waffle, 74 squares: 59 construction / 15 operations | facts.csv (JLARC) | Four in five jobs leave when the building is done |
| 4 Costs | H1 | HTML | PJM capacity price by delivery year, cap line, uncapped simulation | facts.csv (PJM) | Three auctions in a row hit the ceiling |
| 4 | F4 | Flourish | Stacked bars: data-center-attributed vs other capacity charges | facts.csv (IMM) | Nearly half of four auctions' capacity bill traces to data centers |
| 4 | DW3 | Datawrapper | Bill impacts: 2025 jump vs 2026 increment, by utility | facts.csv (IEEFA, MD OPC, PECO) | The big jump came in 2025 |
| 4 | H2 | HTML | Virginia exemption FY23–FY25 with toggle for new tax cap | facts.csv (JLARC, Va. Tax RD40, HB 30) | The tax break grew faster than the new tax can recoup |
| Counterpoint | P1 | Plotly | Scatter: state sales growth vs real price change, 2019–2024 | EIA + BLS CPI | Growth alone didn't raise prices |
| Ending | DW4 | Datawrapper | Searchable table: who wins / who pays | facts.csv | The ledger |

Counts: Datawrapper 4, Flourish 4, Plotly 3, HTML 3 = 14.

## Narrative guardrails (apply to every chart title and annotation)
- Data centers are the largest single driver of PJM capacity-cost increases (IMM). Do not say data centers caused all bill increases.
- Always state units: $/MW-day (capacity), ¢/kWh (retail), $/month (bills), TWh (energy).
- Always state report year AND target year for forecasts.
- PJM peak is 2027/28 ($333.44), not 2028/29. 2028/29 cleared at the cap ($325.00).
- Virginia tax figures are self-reported, state + local; label them that way.
- Census construction figures are nominal and exclude servers/racks.
