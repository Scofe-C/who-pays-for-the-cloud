# Methods page: text for Google Sites

Paste-ready text for the Methods page. Items marked **[confirm]** need your check before publishing.

---

## Colors

| Role | Hex |
|---|---|
| Background | #F7F5F0 |
| Text | #1F1F1F |
| Secondary text | #5E5E5E |
| Gridlines, borders | #D9D6CF |
| Costs / who pays | #B3452C |
| Gains / who wins | #2F5D50 |
| Baseline, neutral series | #3C5A78 |
| Price caps, forecasts (lines only; text in this role uses #7A5C14) | #C99A2E |
| De-emphasized data | #BFB8AC |

The data-center map (DW1) uses a six-step blue scale. The breaks are 1, 10, 50, 100 and 200 records, and the colors are #E9ECEF, #C3CED8, #93A8BC, #62809D, #3C5A78 and #1E3348.

## Fonts

- **Charts built in code** (Plotly P1–P3, custom HTML H1–H3, opening illustration):
  - Source Serif 4 for titles.
  - Source Sans 3 for body text and labels.
  - IBM Plex Mono for numbers and source lines.
  - Fallbacks are Georgia, Arial and Courier New. All fonts come from Google Fonts.
- **Datawrapper charts:** [confirm].
- **Flourish charts:** [confirm].
- **Site text** uses the Google Sites theme font.

## Charts

14 interactive charts:
- **Datawrapper (4):** DW1, DW2, DW3, DW4.
- **Flourish (4):** F1, F2, F3, F4.
- **Plotly (3):** P1, P2, P3.
- **Custom HTML/SVG (3):** H1, H2, H3.
- **Opening illustration:** an extra decorative custom HTML/SVG piece that isn't counted as a chart.

The Plotly and custom HTML charts are hosted on GitHub Pages: https://scofe-c.github.io/who-pays-for-the-cloud/

## Data and cleaning

Five datasets were cleaned with scripts, and report figures were entered by hand into one checked table. Every step is logged in the [cleaning log](https://github.com/Scofe-C/who-pays-for-the-cloud/blob/main/notes/cleaning_log.md).

1. **U.S. Census Bureau, construction spending:** monthly private spending from January 2018 to the latest release, seasonally adjusted annual rate, for data centers and general office buildings. The release vintage is recorded. Figures are nominal and exclude servers and racks.
2. **U.S. EIA retail electricity sales and prices, with BLS CPI-U:** 50 states plus D.C., 2019 and 2024. Prices are converted to 2024 dollars using CPI-U annual averages (the mean of 12 months), and each state is tagged with its PJM membership.
3. **SEC EDGAR filings (Microsoft, Alphabet, Amazon, Meta, Oracle):** capital spending (purchases of property and equipment).
   - Year-to-date values are converted to single quarters, keeping the most recent filing for each period.
   - Fiscal quarters are mapped to calendar quarters.
   - Each value is a trailing four-quarter sum, left blank if any quarter is missing.
   - Derived quarters were checked against figures the companies report themselves.
4. **PNNL IM3 Open Source Data Center Atlas (from OpenStreetMap):** Puerto Rico removed and duplicates removed (5).
   - Facilities are counted by state.
   - Building footprint area is summed by county, from the building layer only, because campus outlines overlap buildings.
5. **EPRI, *Powering Intelligence* (2024), state table:** parsed from the PDF and checked against Virginia's published figure (33,851,122 MWh, 25.59%). The 7 jurisdictions missing from the table are left blank, not set to zero.

**Report figures (facts.csv):**
- 61 numbers from PJM, the PJM market monitor (Monitoring Analytics), LBNL, EPRI, IEA, JLARC, the Virginia Department of Taxation, IEEFA, Maryland OPC and others.
- One row per number. Each row has the source link, the page, a quote of 25 words or fewer, and the initials of the person who checked it.
- Values that combine two figures (for example, a difference) are labeled as derived.

The files uploaded to Datawrapper and Flourish are regenerated from the cleaned data by a script and compared with the hand-prepared versions. Every difference is explained in the run report.

## Use of AI

Claude (Anthropic) drafted the data-cleaning and chart code and some explanatory text. The human author checked every figure against its source page; the `verified_by` column in `facts.csv` records who checked each one. The author also built the Datawrapper and Flourish charts, wrote the narrative, and reviewed each AI-built chart against a checklist (`notes/chart_reviews.md`).

## Licenses and attribution

- **Data-center locations:** PNNL IM3 Open Source Data Center Atlas, © OpenStreetMap contributors, under the Open Database License (ODbL 1.0). Derived data in this project is published under the same license.
- **IEA figures:** from IEA reports, licensed CC BY 4.0. [confirm]
- **U.S. government data:** Census Bureau, EIA, BLS and SEC EDGAR.
- **Trademarks:** company logos and names are trademarks of their owners.
