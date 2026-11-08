# DEPLOY.md

## Task 0 — Embed spike (throwaway, do first)
1. Build one minimal Plotly page with `include_plotlyjs="cdn"` → `docs/charts/spike.html`.
2. Push; enable GitHub Pages (source: branch `main`, folder `/docs`).
3. Human embeds the page URL in a Google Sites test page; checks desktop and phone, hover works, records iframe height.
4. If the URL embed fails, try pasting the HTML as embed code. Report the result; delete the spike afterwards.

## Publishing
- Pages root: `docs/` (`index.html` + `charts/*.html`). Project notes live in `docs-project/`, not in `docs/`.
- `docs/index.html`: list the 6 charts with tool, fonts, and hex values (feeds the "list hex and fonts" requirement).
- Each chart has a stable URL; never rename after it is embedded.

## Licensing
- Repo and Pages are public. IM3-derived files in `data/clean/` are under ODbL 1.0 (`LICENSE-ODbL.txt`) with "© OpenStreetMap contributors".
- Every page that shows IM3-derived data carries the same attribution.

## Before every commit
1. `python scripts/check_secrets.py` passes.
2. `python scripts/validate_facts.py` passes.
3. No file in `data/raw/` modified (`git status`).
4. Charts open locally and at 380px width.
