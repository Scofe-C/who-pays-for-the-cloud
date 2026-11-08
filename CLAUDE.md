# CLAUDE.md — IE 6600 Project 1: "Who Pays for the Cloud?"

Interactive data story on the AI data-center boom: who wins, who pays.
Public site on Google Sites. This repo produces cleaned data plus 6 interactive charts hosted on GitHub Pages.

## Stack
- Python 3 (whatever is installed locally). Deps: requests, pandas, openpyxl, pdfplumber, plotly, python-dotenv.
  Lock with `pip freeze > requirements.txt` after install. Do not invent version numbers.
- Charts: Plotly (exported HTML, plotly.js from CDN) and hand-written HTML/SVG/vanilla JS.
- Hosting: GitHub Pages from `docs/`. Embedded into Google Sites by URL.

## Architecture
```
scripts/        fetch_*.py, clean_*.py, build_charts.py, validate_facts.py, check_secrets.py
data/raw/       original downloads, read-only, filename carries download date
data/manual/    facts.csv (hand-entered report figures, one row per number)
data/clean/     one CSV per chart
docs/           GitHub Pages root: index.html + charts/*.html
notes/          cleaning_log.md
```

## Conventions
- `pathlib` for every path. No shell-specific commands inside scripts (Windows dev, static Linux hosting).
- Every number in a chart traces to a file in `data/raw/` or a row in `data/manual/facts.csv`.
- Every chart shows units on its axes and a source line with the data snapshot date.
- Chart data is embedded in the page as static JSON. No API calls at runtime.

## Do Not
- Never generate, estimate, interpolate, or "fill in" data values. Missing → stop and report.
- Never edit files in `data/raw/`.
- Never put secrets (`EIA_API_KEY`, `SEC_USER_AGENT`) in code, output files, or HTML. They live only in `.env`.
- Never add a dependency not listed above without asking.
- Do not build the Datawrapper or Flourish charts. Only produce their clean CSVs.
- Do not change a figure in `facts.csv` without a source URL and page. Never fill `verified_by` — that column is the human's.

## Commands
```
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # macOS/Linux
pip install -r requirements.txt
python scripts/check_secrets.py   # run before every commit
python scripts/draft_facts.py      # Claude Code drafts, human verifies
python scripts/validate_facts.py
python scripts/build_charts.py
python -m http.server 8000 -d docs   # local preview
```

## Environment
- `.env` (gitignored): `EIA_API_KEY=...`, `SEC_USER_AGENT=Full Name email@domain`
- SEC requests: at most 10 per second.

## Detail files — read the one that matches the task
- `docs-project/PROJECT_BRIEF.md` — story, grading, the 14-chart list, who builds what
- `docs-project/DATA_SOURCES.md` — every dataset and report: URL, how to get it, license, caveats
- `docs-project/DATA_PIPELINE.md` — ordered tasks, cleaning rules, acceptance criteria
- `docs-project/CHART_SPECS.md` — specs for P1–P3 and H1–H3, design tokens, accessibility
- `docs-project/DEPLOY.md` — GitHub Pages, Google Sites embed, licensing, pre-commit checks

## Current Focus
Phase 0: embed spike (see DEPLOY.md). Phase 1: data pipeline (DATA_PIPELINE.md tasks 1–8).
No chart building until Phase 1 acceptance criteria pass.