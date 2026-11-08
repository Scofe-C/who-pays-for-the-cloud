"""Build the Plotly charts P1-P3 into docs/charts/ (CHART_SPECS.md).

- Every number comes from data/clean/*.csv; nothing typed. Title claims are checked against
  the data and the build fails if a claim does not hold.
- Each page is standalone: data inlined, plotly.js from CDN, Google Fonts link, works from file://.
- Controls are real <select>/<button> elements with labels (not Plotly updatemenus).
"""

from __future__ import annotations

import html
import json
import logging
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

ROOT = Path(__file__).resolve().parents[1]
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "docs" / "charts"

# Design tokens (CHART_SPECS.md)
BG, TEXT, TEXT2, GRID = "#F7F5F0", "#1F1F1F", "#5E5E5E", "#D9D6CF"
COST, GAIN, NEUTRAL, CAP, CAP_TEXT, MUTED = "#B3452C", "#2F5D50", "#3C5A78", "#C99A2E", "#7A5C14", "#BFB8AC"
SANS, SERIF, MONO = "'Source Sans 3', Arial, sans-serif", "'Source Serif 4', Georgia, serif", "'IBM Plex Mono', 'Courier New', monospace"
FONTS = ("https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@600&family=Source+Sans+3:wght@400;600"
         "&family=IBM+Plex+Mono:wght@400&display=swap")
PLOTLY_CONFIG = {"responsive": True, "displaylogo": False,
                 "modeBarButtonsToRemove": ["select2d", "lasso2d", "autoScale2d", "toggleSpikelines"]}

log = logging.getLogger("build_charts")


def fail(msg: str) -> None:
    log.error(msg)
    sys.exit(1)


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def js_json(obj) -> str:
    """JSON safe to inline inside <script>."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def snapshot(source: str) -> str:
    m = re.search(r"downloaded (\d{4}-\d{2}-\d{2})", source)
    return m.group(1) if m else ""


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{fonts}">
<style>
:root {{ --bg:{bg}; --text:{text}; --text2:{text2}; --grid:{grid}; --cost:{cost}; --gain:{gain};
        --neutral:{neutral}; --cap:{cap}; --captext:{captext}; --muted:{muted}; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; background: var(--bg); color: var(--text); }}
body {{ font-family: {sans}; font-size: 16px; line-height: 1.45; }}
main {{ max-width: 860px; margin: 0 auto; padding: 16px; }}
h1 {{ font-family: {serif}; font-weight: 600; font-size: clamp(1.25rem, 4.5vw, 1.75rem); line-height: 1.2; margin: 0 0 6px; }}
.subtitle {{ color: var(--text2); margin: 0 0 12px; }}
.controls {{ display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; margin: 0 0 8px; }}
.controls label {{ font-weight: 600; }}
select, button {{ font: inherit; min-height: 44px; padding: 6px 12px; border: 1px solid var(--text2);
                 border-radius: 4px; background: #fff; color: var(--text); cursor: pointer; }}
button[aria-pressed="true"] {{ background: var(--text); color: var(--bg); }}
select:focus-visible, button:focus-visible {{ outline: 3px solid var(--neutral); outline-offset: 2px; }}
.chart {{ width: 100%; min-height: 300px; position: relative; }}
.chart svg {{ display: block; overflow: visible; }}
.chart svg text {{ font-family: {sans}; fill: var(--text); }}
.tip {{ position: absolute; display: none; pointer-events: none; background: #fff; border: 1px solid var(--grid);
       border-radius: 4px; padding: 6px 8px; font-size: 0.85rem; line-height: 1.35; max-width: 260px;
       box-shadow: 0 2px 6px rgba(0,0,0,.12); z-index: 2; }}
.key {{ font-size: 0.9rem; color: var(--text2); margin: 4px 0 0; }}
.live {{ min-height: 2.9em; margin: 8px 0 0; }}
.note {{ color: var(--text2); font-size: 0.9rem; margin: 8px 0 0; }}
.source {{ font-family: {mono}; font-size: 0.75rem; color: var(--text2); margin: 12px 0 0; overflow-wrap: anywhere; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; animation: none !important; }} }}
</style>
</head>
<body>
<main>
<h1>{title}</h1>
<p class="subtitle">{subtitle}</p>
{controls}
<div class="chart"{role}>
{chart}
</div>
{notes}
<p class="source">{source}</p>
</main>
{script}
</body>
</html>
"""


def page(path: Path, *, title: str, subtitle: str, aria: str, chart: str, source: str,
         notes: list[str] = (), controls: str = "", script: str = "", img_role: bool = True) -> None:
    out = PAGE.format(
        title=esc(title), subtitle=subtitle, chart=chart,
        role=f' role="img" aria-label="{esc(aria)}"' if img_role else "", source=source, controls=controls,
        notes="\n".join(f'<p class="note">{n}</p>' for n in notes), script=script, fonts=FONTS,
        bg=BG, text=TEXT, text2=TEXT2, grid=GRID, cost=COST, gain=GAIN, neutral=NEUTRAL, cap=CAP,
        captext=CAP_TEXT, muted=MUTED, sans=SANS, serif=SERIF, mono=MONO)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(out, encoding="utf-8", newline="\n")
    log.info("wrote %s (%.0f KB)", path.relative_to(ROOT), path.stat().st_size / 1024)


def base_layout(**kw) -> dict:
    axis = dict(showgrid=False, zerolinecolor=TEXT2, linecolor=TEXT2, tickfont=dict(family=SANS, size=13),
                title=dict(font=dict(family=SANS, size=14, color=TEXT)))
    layout = dict(paper_bgcolor=BG, plot_bgcolor=BG, font=dict(family=SANS, color=TEXT, size=13),
                  margin=dict(l=60, r=16, t=16, b=60), hoverlabel=dict(font=dict(family=SANS, size=13)),
                  xaxis=dict(axis), yaxis=dict(axis),
                  legend=dict(orientation="h", yanchor="top", y=-0.2, x=0, font=dict(size=13)))
    for k, v in kw.items():
        if k in ("xaxis", "yaxis"):
            layout[k] = {**layout[k], **v}
        else:
            layout[k] = v
    return layout


def plotly_div(fig: go.Figure, div_id: str, height: int, post_script: str | None = None) -> str:
    return pio.to_html(fig, full_html=False, include_plotlyjs="cdn", div_id=div_id, config=PLOTLY_CONFIG,
                       default_height=f"{height}px", post_script=post_script)


# ---------------------------------------------------------------- P1
def p1() -> None:
    d = pd.read_csv(CLEAN / "p1_state_price_growth.csv")
    if len(d) != 51:
        fail(f"P1: expected 51 rows, got {len(d)}")
    x, y = d["sales_change_pct"].to_numpy(), d["price_change_pct"].to_numpy()
    slope, intercept = np.polyfit(x, y, 1)
    r = float(np.corrcoef(x, y)[0, 1])
    if slope >= 0:
        fail(f"P1: OLS slope {slope:.3f} is not negative; spec title does not hold")
    log.info("P1 OLS slope %.3f, intercept %.2f, r %.3f", slope, intercept, r)

    status = {"full": "PJM (whole state)", "partial": "PJM (part of state)", "no": "Not in PJM"}
    custom = np.stack([d["state"], d["pjm"].map(status), d["price_real_2019_cents"].round(2),
                       d["price_real_2024_cents"]], axis=-1)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="markers", name="State", customdata=custom, showlegend=False,
        marker=dict(size=11, color=NEUTRAL, opacity=0.85, line=dict(width=1, color=BG)),
        hovertemplate=("<b>%{customdata[0]}</b><br>Sales change: %{x:.1f}%<br>Real price change: %{y:.1f}%<br>"
                       "Avg price: %{customdata[2]}¢ → %{customdata[3]}¢ per kWh (2024 dollars)<br>"
                       "%{customdata[1]}<extra></extra>")))
    # State labels: Virginia (the story's focus) plus the data's extremes, chosen from the data.
    lab = {"VA", d.loc[d["sales_change_pct"].idxmax(), "state"], d.loc[d["price_change_pct"].idxmax(), "state"],
           d.loc[d["sales_change_pct"].idxmin(), "state"]}
    m = d["state"].isin(lab)
    fig.add_trace(go.Scatter(x=x[m], y=y[m], mode="text", text=[" " + t for t in d.loc[m, "state"]], textposition="middle right",
                             textfont=dict(family=SANS, size=12, color=TEXT), hoverinfo="skip", showlegend=False))
    up, pu = d["sales_change_pct"] > 0, d["price_change_pct"] > 0
    q = {(True, False): int((up & ~pu).sum()), (True, True): int((up & pu).sum()),
         (False, True): int((~up & pu).sum()), (False, False): int((~up & ~pu).sum())}
    for (u, p_), (ax, ay, xa, ya) in {(True, False): (1, 0.4, "right", "middle"), (True, True): (1, 1, "right", "top"),
                                      (False, True): (0, 1, "left", "top"), (False, False): (0, 0, "left", "bottom")}.items():
        strong = (u, p_) == (True, False)
        fig.add_annotation(xref="paper", yref="paper", x=ax, y=ay, xanchor=xa, yanchor=ya, showarrow=False,
                           text=(f"<b>Sold more, price fell: {q[(u, p_)]}</b>" if strong else
                                 f"Sold {'more' if u else 'less'}, price {'rose' if p_ else 'fell'}: {q[(u, p_)]}"),
                           font=dict(family=SANS, size=12, color=GAIN if strong else TEXT2), bgcolor=BG)
    n_up, n_up_fell = int(up.sum()), q[(True, False)]
    xs = np.array([x.min(), x.max()])
    fig.add_trace(go.Scatter(
        x=xs, y=intercept + slope * xs, mode="lines", name="Trend (OLS)", hoverinfo="skip", showlegend=False,
        line=dict(color=TEXT2, width=2, dash="dash")))
    tx = x.max() * 0.68  # label sits above the line in the empty lower-right area
    fig.add_annotation(x=tx, y=intercept + slope * tx, text=f"Trend, r = {r:.2f}",
                       showarrow=False, xanchor="left", yanchor="bottom", yshift=4,
                       font=dict(family=SANS, size=12, color=TEXT2), bgcolor=BG)
    fig.update_layout(**base_layout(
        xaxis=dict(title=dict(text="Electricity sold, change 2019–2024"), ticksuffix="%"),
        yaxis=dict(title=dict(text="Price after inflation, change"), ticksuffix="%",
                   range=[y.min() - 4, y.max() + 8])))  # headroom so corner labels clear the top dot

    colors = {"none": [NEUTRAL] * len(d),
              "pjm": [COST if p == "full" else COST if p == "partial" else MUTED for p in d["pjm"]]}
    symbols = {"none": ["circle"] * len(d),
               "pjm": ["circle" if p == "full" else "circle-open" if p == "partial" else "circle" for p in d["pjm"]]}
    script = f"""<script>
(function () {{
  var colors = {js_json(colors)}, symbols = {js_json(symbols)};
  var sel = document.getElementById('p1-highlight');
  sel.addEventListener('change', function () {{
    var k = sel.value;
    Plotly.restyle('p1-plot', {{'marker.color': [colors[k]], 'marker.symbol': [symbols[k]]}}, [0]);
    document.getElementById('p1-key').hidden = (k !== 'pjm');
  }});
}})();
</script>"""
    controls = ('<div class="controls"><label for="p1-highlight">Highlight</label>'
                '<select id="p1-highlight"><option value="none">None</option>'
                '<option value="pjm">PJM states</option></select>'
                f'<span id="p1-key" class="note" hidden><span style="color:{COST}">●</span> whole state in PJM '
                f'&nbsp;<span style="color:{COST}">○</span> part of state in PJM '
                f'&nbsp;<span style="color:{MUTED}">●</span> not in PJM</span></div>')
    snap = snapshot(d["source"].iloc[0])
    page(OUT / "p1.html",
         title="Growth alone didn’t raise prices",
         subtitle=(f"Of the {n_up} states whose electricity sales grew from 2019 to 2024, {n_up_fell} saw "
                   f"their average power price fall after inflation. Each dot is a state or D.C.; "
                   f"right = sold more, down = cheaper."),
         aria=(f"Scatter plot of {len(d)} states and D.C.: change in retail electricity sales 2019 to 2024 "
               f"against real price change. The trend line slopes downward (r = {r:.2f})."),
         chart=plotly_div(fig, "p1-plot", 480), controls=controls, script=script,
         notes=["All sectors, annual averages. Real price = nominal average retail price deflated with CPI-U "
                "(annual mean of 12 months) to 2024 dollars.",
                "PJM status: membership per pjm.com; the whole-state vs part-of-state split is our classification."],
         source=f"Source: U.S. EIA, electricity retail sales (API v2); BLS CPI-U (CUUR0000SA0). Data snapshot {snap}.")


# ---------------------------------------------------------------- P2
def p2() -> None:
    d = pd.read_csv(CLEAN / "p2_construction.csv")
    w = d.pivot(index="month", columns="series", values="value_musd_saar").sort_index()
    st = d.pivot(index="month", columns="series", values="status").sort_index().fillna("")
    latest = w.index.max()
    if not w.loc[latest, "data_center"] > w.loc[latest, "general_office"]:
        fail("P2: latest month data centers not above general office; title does not hold")
    above = w["data_center"] > w["general_office"]
    since = above[::-1].cumprod()[::-1]  # True where every month from here on is above
    since_month = since[since.astype(bool)].index.min()
    since_txt = pd.Period(since_month, "M").strftime("%B %Y")
    latest_txt = pd.Period(latest, "M").strftime("%B %Y")
    first = pd.Period(w.index.min(), "M").strftime("%B %Y")
    log.info("P2 data centers above general office every month since %s", since_month)

    first_cross = above.idxmax()
    fig = go.Figure()
    for key, name, color in [("data_center", "Data centers", COST), ("general_office", "General office", NEUTRAL)]:
        fig.add_trace(go.Scatter(
            x=pd.to_datetime(w.index), y=(w[key] / 1000).round(2), name=name, mode="lines",
            line=dict(color=color, width=2.5), customdata=st[key].replace({"": "final"}),
            hovertemplate=f"<b>{name}</b><br>%{{x|%B %Y}}<br>$%{{y:.1f}}B (SAAR)<br>%{{customdata}}<extra></extra>"))
        end = w[key].iloc[-1] / 1000
        fig.add_annotation(x=pd.to_datetime(latest), y=end, text=f"<b>{name}</b> ${end:.1f}B", showarrow=False,
                           xanchor="right", yanchor="bottom" if key == "data_center" else "top",
                           yshift=6 if key == "data_center" else -6, font=dict(family=SANS, size=13, color=color))
    cx, cdc, cgo = pd.to_datetime(since_month), w.loc[since_month, "data_center"] / 1000, w.loc[since_month, "general_office"] / 1000
    fig.add_annotation(x=cx, y=cdc, ax=-110, ay=-125, showarrow=True, arrowhead=0, arrowwidth=1, arrowcolor=TEXT2,
                       text=(f"<b>{pd.Period(since_month, 'M').strftime('%b %Y')}</b>: data centers<br>pass for good, "
                             f"${cdc:.1f}B<br>vs ${cgo:.1f}B office"),
                       align="left", bgcolor=BG, font=dict(family=SANS, size=12, color=TEXT))
    fig.update_layout(**base_layout(
        hovermode="x unified",
        xaxis=dict(rangeslider=dict(visible=True, thickness=0.08, bgcolor="#EFEBE3"), type="date"),
        yaxis=dict(title=dict(text="Billion dollars, seasonally adjusted annual rate"), tickprefix="$",
                   rangemode="tozero"),
        showlegend=False, margin=dict(l=60, r=16, t=16, b=40)))
    page(OUT / "p2.html",
         title="Data-center construction now outspends general office buildings",
         subtitle=(f"Private construction spending, monthly, {first} to {latest_txt}. "
                   f"Data centers have been above general office every month since {since_txt}."),
         aria=(f"Line chart of monthly private construction spending for data centers and general office buildings, "
               f"{first} to {latest_txt}. Data centers rise steeply and stay above general office from {since_txt}."),
         chart=plotly_div(fig, "p2-plot", 480),
         notes=["Nominal dollars. Construction spending covers buildings and their systems; servers and racks are "
                "not included.",
                "General office = the Census “General” office subcategory (the Census “Office” total includes data "
                f"centers). Recent months are preliminary or revised; {latest_txt} is preliminary.",
                f"The lines first crossed in {pd.Period(first_cross, 'M').strftime('%B %Y')}, then traded places "
                f"until {since_txt}."],
         source=f"Source: {esc(d['source'].iloc[0])}.")


# ---------------------------------------------------------------- P3
def p3() -> None:
    d = pd.read_csv(CLEAN / "p3_iea.csv").sort_values("year")
    if list(d["year"]) != [2023, 2024, 2025, 2030]:
        fail(f"P3: expected years 2023/2024/2025/2030, got {list(d['year'])}")
    v = d.set_index("year")["twh"]
    ratio = v[2030] / v[2025]
    if not 1.8 <= ratio < 2.0:
        fail(f"P3: 2030/2025 ratio {ratio:.2f} does not fit 'nearly doubles'")
    proj = d["kind"].str.startswith("projection")
    short = d["report"].str.replace(r", full report PDF$", "", regex=True)
    labels = [f"{y} (projection)" if p else str(y) for y, p in zip(d["year"], proj)]
    vals = d["twh"].round(0).astype(int).tolist()
    custom = np.stack([short, d["kind"]], axis=-1)

    fig = go.Figure(go.Bar(
        x=[0] * len(d), y=labels, orientation="h", customdata=custom,
        text=[f"{x:,} TWh" for x in vals], textposition="outside", cliponaxis=False,
        textfont=dict(family=MONO, size=13, color=TEXT),
        marker=dict(color=[COST if p else NEUTRAL for p in proj], line=dict(color=[COST if p else NEUTRAL for p in proj], width=1.5),
                    pattern=dict(shape=["/" if p else "" for p in proj], fgcolor=BG, fgopacity=0.6, size=8)),
        hovertemplate="<b>%{y}</b><br>%{customdata[1]}: %{x:,.0f} TWh<br>%{customdata[0]}<extra></extra>"))
    fig.update_layout(**base_layout(
        xaxis=dict(title=dict(text="Electricity use (TWh)"),
                   range=[0, max(vals) * 1.3], fixedrange=True),
        yaxis=dict(autorange="reversed", fixedrange=True),
        margin=dict(l=110, r=24, t=8, b=56), showlegend=False, bargap=0.35))
    post = f"""
var gd = document.getElementById('{{plot_id}}');
var vals = {js_json(vals)};
var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
// Grow-in: restyle per animation frame (full layout each frame keeps outside labels placed).
if (reduce) {{ Plotly.restyle(gd, {{x: [vals]}}, [0]); }}
else {{
  var t0 = null, dur = 900;
  var step = function (ts) {{
    if (t0 === null) t0 = ts;
    var k = Math.min(1, (ts - t0) / dur), e = 1 - Math.pow(1 - k, 3);
    Plotly.restyle(gd, {{x: [vals.map(function (v) {{ return v * e; }})]}}, [0]);
    if (k < 1) window.requestAnimationFrame(step);
  }};
  window.requestAnimationFrame(step);
}}
"""
    src = sorted(set(short))
    note23 = d.loc[d["year"] == 2023, "notes"].iloc[0].split("; page =")[0]  # drop local-file pointer
    page(OUT / "p3.html",
         title="Global data-center electricity use nearly doubles by 2030",
         subtitle=(f"From {vals[2]:,} TWh in 2025 to {vals[3]:,} TWh in 2030 in the IEA Base Case "
                   f"(projection, report year 2026). Hover a bar for its source."),
         aria=(f"Horizontal bar chart of global data-center electricity use: " +
               ", ".join(f"{lab} {x:,} TWh" for lab, x in zip(labels, vals)) + "."),
         chart=plotly_div(fig, "p3-plot", 340, post_script=post),
         notes=["Hatched bar = projection. 2024 comes from IEA Energy and AI (2025); 2023, 2025 and 2030 come from "
                "IEA Key Questions on Energy and AI (2026).",
                f"2023 value: {esc(note23)}."],
         source=f"Source: {'; '.join(esc(s) for s in src)}. IEA, CC BY 4.0. Data snapshot {d['as_of'].iloc[0]}.")


# ---------------------------------------------------------------- shared JS for H1-H3 (vanilla SVG)
COMMON_JS = r"""
var NS = 'http://www.w3.org/2000/svg';
function el(tag, attrs, parent) { var e = document.createElementNS(NS, tag);
  for (var k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; }
function txt(parent, x, y, s, attrs) { var a = attrs || {}; a.x = x; a.y = y; var t = el('text', a, parent);
  t.textContent = s; return t; }
function makeTip(box) { var tip = document.createElement('div'); tip.className = 'tip'; tip.setAttribute('role', 'tooltip');
  box.appendChild(tip);
  return { show: function (html, x, y) { tip.innerHTML = html; tip.style.display = 'block';
      var w = box.clientWidth, tw = tip.offsetWidth;
      tip.style.left = Math.min(Math.max(0, x - tw / 2), w - tw) + 'px';
      tip.style.top = Math.max(0, y - tip.offsetHeight - 10) + 'px'; },
    hide: function () { tip.style.display = 'none'; } }; }
function bindTip(node, tip, box, html) {
  function s() { var r = node.getBoundingClientRect(), b = box.getBoundingClientRect();
    tip.show(html, r.left - b.left + r.width / 2, r.top - b.top); }
  node.addEventListener('mouseenter', s); node.addEventListener('mouseleave', tip.hide); }
function onResize(fn) { var t, w0 = window.innerWidth; window.addEventListener('resize', function () {
  if (window.innerWidth === w0) return; w0 = window.innerWidth; clearTimeout(t); t = setTimeout(fn, 120); }); }
function money(n, d) { return '$' + n.toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d}); }
function newSvg(box, W, H, label) { var svg = el('svg', {width: W, height: H, viewBox: '0 0 ' + W + ' ' + H,
  role: 'img', 'aria-label': label}); box.insertBefore(svg, box.firstChild); return svg; }
"""


def h_script(data: dict, body: str) -> str:
    return "<script>\n(function () {\n" + COMMON_JS + "var D = " + js_json(data) + ";\n" + body + "\n})();\n</script>"


def col_tokens() -> dict:
    return {"cost": COST, "gain": GAIN, "neutral": NEUTRAL, "cap": CAP, "captext": CAP_TEXT, "muted": MUTED,
            "text": TEXT, "text2": TEXT2, "bg": BG, "mono": MONO}


# ---------------------------------------------------------------- H1
H1_JS = r"""
var box = document.getElementById('h1-chart'), tip, sel = D.years.length - 1, c = D.c;
var noteEl = document.getElementById('h1-note');
function render() {
  box.innerHTML = ''; tip = makeTip(box);
  var W = box.clientWidth, H = Math.max(300, Math.min(420, W * 0.62)), m = {l: 52, r: 12, t: 28, b: 34};
  var svg = newSvg(box, W, H, 'Column chart of PJM capacity clearing prices by delivery year, in dollars per megawatt-day: ' +
      D.years.map(function (y, i) { return y + ' $' + D.prices[i]; }).join(', ') + '.');
  var top = Math.max.apply(null, D.prices.concat(D.uncapped.filter(function (v) { return v; }))) * 1.12;
  var ih = H - m.t - m.b, iw = W - m.l - m.r, y = function (v) { return m.t + ih - v / top * ih; };
  var step = top > 400 ? 100 : 50;
  for (var t = 0; t <= top; t += step) {
    txt(svg, m.l - 8, y(t) + 4, '$' + t, {'text-anchor': 'end', 'font-size': 12, fill: c.text2}); }
  el('line', {x1: m.l, x2: m.l + iw, y1: y(0), y2: y(0), stroke: c.text2}, svg);
  txt(svg, 0, 14, '$/MW-day', {'font-size': 12, fill: c.text2});
  var band = iw / D.years.length, bw = Math.min(64, band * 0.62);
  D.years.forEach(function (yr, i) {
    var cx = m.l + band * (i + 0.5), v = D.prices[i];
    var r = el('rect', {x: cx - bw / 2, y: y(v), width: bw, height: y(0) - y(v), fill: c.cost,
      opacity: i === sel ? 1 : 0.45, style: 'cursor:pointer'}, svg);
    r.addEventListener('click', function () { select(i); });
    bindTip(r, tip, box, '<b>' + yr + '</b><br>' + money(v, 2) + ' per MW-day' +
      (D.atCap[i] ? '<br>Cleared at the price cap' : '') +
      (D.uncapped[i] ? '<br>Without cap and floor (PJM simulation): ' + money(D.uncapped[i], 2) : ''));
    txt(svg, cx, y(v) - 9, money(v, 0), {'text-anchor': 'middle', 'font-size': 12,
      'font-family': c.mono, 'font-weight': i === sel ? 600 : 400});
    txt(svg, cx, y(0) + 20, yr, {'text-anchor': 'middle', 'font-size': 12, 'font-weight': i === sel ? 600 : 400});
    if (D.atCap[i]) el('line', {x1: cx - bw / 2 - 6, x2: cx + bw / 2 + 6, y1: y(v), y2: y(v), stroke: c.cap,
      'stroke-width': 3, 'stroke-dasharray': '6 4'}, svg);
    if (D.uncapped[i]) {
      el('line', {x1: cx, x2: cx, y1: y(v) - 24, y2: y(D.uncapped[i]) + 8, stroke: c.cost,
        'stroke-width': 1.5, 'stroke-dasharray': '2 3'}, svg);
      var ci = el('circle', {cx: cx, cy: y(D.uncapped[i]), r: 7, fill: c.bg, stroke: c.cost, 'stroke-width': 2.5}, svg);
      bindTip(ci, tip, box, '<b>' + yr + ' without the cap</b><br>PJM simulation: ' + money(D.uncapped[i], 2) + ' per MW-day');
      txt(svg, cx - 12, y(D.uncapped[i]) + 4, money(D.uncapped[i], 2) + ' without the cap',
        {'text-anchor': 'end', 'font-size': 12, fill: c.cost});
    }
  });
}
function select(i) {
  sel = i; noteEl.textContent = D.notes[i];
  document.querySelectorAll('#h1-buttons button').forEach(function (b, j) { b.setAttribute('aria-pressed', j === i); });
  render();
}
document.querySelectorAll('#h1-buttons button').forEach(function (b, j) { b.addEventListener('click', function () { select(j); }); });
onResize(render); select(sel);
"""


def h1() -> None:
    d = pd.read_csv(CLEAN / "h1_pjm.csv", dtype={"at_cap": str})
    d["at_cap"] = d["at_cap"].fillna("") == "True"
    prices = d["price_usd_mw_day"].astype(float).tolist()
    years = d["delivery_year"].tolist()
    # Title: consecutive at-cap auctions ending with the latest one (from at_cap, never typed).
    run = 0
    for capped in reversed(d["at_cap"].tolist()):
        if not capped:
            break
        run += 1
    titles = {1: "The latest auction hit the price cap", 2: "The last two auctions hit the price cap",
              3: "Three auctions in a row hit the ceiling"}
    if run not in titles:
        fail(f"H1: {run} trailing at-cap auctions; no title wording")
    peak = int(np.argmax(prices))
    unc = pd.to_numeric(d["uncapped_sim_usd_mw_day"], errors="coerce")
    notes = []
    for i, (yr, p, capped) in enumerate(zip(years, prices, d["at_cap"])):
        s = f"{yr}: cleared at ${p:,.2f}/MW-day"
        if i > 0:
            ratio = p / prices[i - 1]
            s += (f", {ratio:.1f}× the year before" if ratio >= 1.5 else
                  f", {(ratio - 1) * 100:+.1f}% from the year before")
        if i == peak:
            s += " (the highest in this series)"
        if capped:
            s += ", at the price cap"
        if not np.isnan(unc.iloc[i]):
            s += f". PJM’s simulation without the cap and floor: ${unc.iloc[i]:,.2f}"
        notes.append(s + ".")
    capped_idx = [i for i, capped in enumerate(d["at_cap"]) if capped]
    unknown = [years[i] for i in range(min(capped_idx), len(years)) if not d["at_cap"].iloc[i]] if capped_idx else []
    unknown += [years[min(capped_idx) - 1]] if capped_idx and min(capped_idx) > 0 else []
    if d.get("at_cap_source", pd.Series(dtype=str)).fillna("").any():
        unknown = []  # 2026/27 cap status sourced from its own report (pjm_2627_at_cap, verified): note dropped
    data = {"years": years, "prices": prices, "atCap": d["at_cap"].tolist(),
            "uncapped": [None if np.isnan(v) else float(v) for v in unc], "notes": notes, "c": col_tokens()}
    buttons = "".join(f'<button type="button" aria-pressed="false">{esc(yr)}</button>' for yr in years)
    src = d.iloc[0]
    page(OUT / "h1.html",
         title=titles[run],
         subtitle=("PJM capacity auction clearing price for the whole region (RTO), by delivery year. "
                   f"The peak was {years[peak]} at ${prices[peak]:,.2f}/MW-day. Pick a year for details."),
         aria="", img_role=False,
         controls=(f'<div class="controls" role="group" aria-label="Delivery year" id="h1-buttons">'
                   f'<span style="font-weight:600">Delivery year</span>{buttons}</div>'),
         chart='<div id="h1-chart"></div>',
         notes=['<span id="h1-note" class="live" aria-live="polite"></span>',
                f'<span class="key"><span style="color:{CAP}">- - -</span> cleared at the price cap &nbsp; '
                f'<span style="color:{COST}">○</span> PJM simulation without the cap and floor</span>',
                "Prices in $/MW-day of unforced capacity (UCAP), RTO clearing price. "
                + (f"The PJM report does not state whether {', '.join(unknown)} cleared at the cap, so "
                   "it has no cap marker." if unknown else "")],
         script=h_script(data, H1_JS),
         source=f"Source: {esc(src['source_title'])}, p. {src['page']}"
                + "".join(f"; {esc(s)} (cap status {yr})" for yr, s in
                          zip(years, d.get("at_cap_source", pd.Series(dtype=str)).fillna("")) if s)
                + f". Data snapshot {src['as_of']}.")


# ---------------------------------------------------------------- H2
H2_JS = r"""
var box = document.getElementById('h2-chart'), btn = document.getElementById('h2-cap'), tip, c = D.c, showCap = false;
function render() {
  box.innerHTML = ''; tip = makeTip(box);
  var W = box.clientWidth, H = Math.max(280, Math.min(380, W * 0.55)), m = {l: 52, r: 12, t: 28, b: 34};
  var svg = newSvg(box, W, H, 'Column chart of the Virginia data center sales tax exemption benefit, self-reported, in billion dollars: ' +
      D.fy.map(function (f, i) { return f + ' $' + D.vals[i].toFixed(2) + 'B'; }).join(', ') +
      (showCap ? '. A dashed line marks the new tax revenue cap of $' + D.cap + 'B a year.' : '.'));
  var top = Math.max.apply(null, D.vals.concat([D.cap])) * 1.18, ih = H - m.t - m.b, iw = W - m.l - m.r;
  var y = function (v) { return m.t + ih - v / top * ih; };
  for (var t = 0; t <= top; t += 0.5) txt(svg, m.l - 8, y(t) + 4, '$' + t.toFixed(1) + 'B',
    {'text-anchor': 'end', 'font-size': 12, fill: c.text2});
  el('line', {x1: m.l, x2: m.l + iw, y1: y(0), y2: y(0), stroke: c.text2}, svg);
  var band = iw / D.fy.length, bw = Math.min(80, band * 0.55);
  D.fy.forEach(function (f, i) {
    var cx = m.l + band * (i + 0.5), v = D.vals[i];
    var r = el('rect', {x: cx - bw / 2, y: y(v), width: bw, height: y(0) - y(v), fill: c.gain}, svg);
    bindTip(r, tip, box, '<b>' + f + '</b><br>' + money(v, 2) + 'B in sales and use tax not paid<br>' +
      'Self-reported by data center operators<br>Source: ' + D.src[i]);
    txt(svg, cx, y(v) - 8, money(v, 2) + 'B', {'text-anchor': 'middle', 'font-size': 13, 'font-family': c.mono});
    txt(svg, cx, y(0) + 20, f, {'text-anchor': 'middle', 'font-size': 12});
  });
  if (showCap) {
    el('line', {x1: m.l, x2: m.l + iw, y1: y(D.cap), y2: y(D.cap), stroke: c.cap, 'stroke-width': 3,
      'stroke-dasharray': '8 5'}, svg);
    var lab = txt(svg, m.l + 6, y(D.cap) - 8, 'New tax: at most ' + money(D.cap, 1) + 'B a year',
      {'font-size': 12, fill: c.captext, 'font-weight': 600, 'paint-order': 'stroke', stroke: c.bg, 'stroke-width': 4});
  }
}
btn.addEventListener('click', function () { showCap = !showCap; btn.setAttribute('aria-pressed', showCap);
  btn.textContent = showCap ? 'Hide the new tax cap' : 'Show the new tax cap'; render(); });
onResize(render); render();
"""


def h2() -> None:
    d = pd.read_csv(CLEAN / "h2_va_tax.csv")
    ex = d[d["series"] == "exemption_benefit"].sort_values("period")
    cap = d[d["series"] == "new_tax_annual_cap"].iloc[0]
    rate = d[d["series"] == "vabudget_rate"].iloc[0]
    ret = d[d["series"] == "jlarc_return_per_dollar"].iloc[0]
    if rate["unit_as_reported"] != "USD per kWh" or not str(ret["unit_as_reported"]).startswith("cents"):
        fail("H2: unexpected units for rate/return")
    vals = ex["value_usd_b"].astype(float).tolist()
    if not vals[-1] > float(cap["value_usd_b"]):
        fail("H2: latest exemption benefit not above the new tax cap; title does not hold")
    cents = float(rate["value_as_reported"]) * 100
    data = {"fy": ex["period"].tolist(), "vals": vals, "cap": float(cap["value_usd_b"]),
            "src": [("JLARC" if "JLARC" in t else "Va. Dept. of Taxation (RD40)") for t in ex["source_title"]],
            "c": col_tokens()}
    page(OUT / "h2.html",
         title="The tax break grew faster than the new tax can recoup",
         subtitle=(f"Virginia’s data center sales and use tax exemption: benefit reported by operators, "
                   f"{ex['period'].iloc[0]} to {ex['period'].iloc[-1]}, $ billions (self-reported, state + local). "
                   f"Toggle to compare the annual revenue cap of the new {cents:.1f}¢/kWh tax."),
         aria="", img_role=False,
         controls='<div class="controls"><button type="button" id="h2-cap" aria-pressed="false">Show the new tax cap</button></div>',
         chart='<div id="h2-chart"></div>',
         notes=[f"JLARC: about {float(ret['value_as_reported']):.0f}¢ of state revenue comes back for every $1 of "
                "exemption.",
                f"{ex['period'].iloc[0]} is from JLARC (state, local and regional sales tax); later years are from the "
                "Virginia Department of Taxation’s RD40 report. All figures are self-reported by operators.",
                f"New tax: {cents:.1f}¢ per kWh {esc(rate['period'])}, revenue capped at "
                f"${float(cap['value_usd_b']):.1f}B a year ({esc(cap['period'])}); amounts above the cap are refunded. "
                "Secondary source (law-firm summary of the budget bill, HB 30)."],
         script=h_script(data, H2_JS),
         source=("Sources: " + "; ".join(esc(t) for t in dict.fromkeys(d["source_title"])) +
                 f". Data snapshot {d['as_of'].iloc[0]}."))


# ---------------------------------------------------------------- H3
H3_JS = r"""
var box = document.getElementById('h3-chart'), tip, c = D.c;
var on = D.cols.map(function () { return true; });
function render() {
  box.innerHTML = ''; tip = makeTip(box);
  var W = box.clientWidth, H = Math.max(330, Math.min(430, W * 0.66)), m = {l: 40, r: 8, t: 64, b: 58};
  var svg = newSvg(box, W, H, 'Data center share of U.S. electricity. Actual: ' +
      D.cols.filter(function (k) { return k.kind === 'actual'; }).map(function (k) { return k.l2 + ' ' + k.v + '%'; }).join(', ') +
      '. Forecast ranges: ' + D.cols.filter(function (k) { return k.kind === 'range'; }).map(function (k) {
        return k.name + ' ' + k.l3 + ', ' + k.lo + ' to ' + k.hi + '%'; }).join('; ') + '.');
  var top = Math.ceil(Math.max.apply(null, D.cols.map(function (k) { return k.hi || k.v; })) / 5) * 5;
  var ih = H - m.t - m.b, iw = W - m.l - m.r, y = function (v) { return m.t + ih - v / top * ih; };
  for (var t = 0; t <= top; t += 5) txt(svg, m.l - 6, y(t) + 4, t + '%', {'text-anchor': 'end', 'font-size': 12, fill: c.text2});
  el('line', {x1: m.l, x2: m.l + iw, y1: y(0), y2: y(0), stroke: c.text2}, svg);
  var band = iw / D.cols.length, small = band < 64;
  D.cols.forEach(function (k, i) {
    var cx = m.l + band * (i + 0.5), g = el('g', {opacity: on[i] ? 1 : 0.12}, svg);
    (small && k.s2 ? [k.l1, k.s2, k.s3] : [k.l1, k.l2, k.l3]).forEach(function (s, j) { if (s) txt(svg, cx, y(0) + 16 + j * 14, s,
      {'text-anchor': 'middle', 'font-size': small ? 10.5 : 12, 'font-weight': j === 0 ? 600 : 400,
       fill: on[i] ? c.text : c.muted}); });
    if (k.kind === 'actual') {
      var dot = el('circle', {cx: cx, cy: y(k.v), r: 7, fill: c.text}, g);
      txt(g, cx, y(k.v) - 12, k.v + '%', {'text-anchor': 'middle', 'font-size': 13, 'font-family': c.mono, 'font-weight': 600});
      bindTip(dot, tip, box, '<b>Actual ' + k.l2 + '</b><br>' + k.v + '% of U.S. electricity<br>' + k.tipsrc);
    } else {
      var bar = el('line', {x1: cx, x2: cx, y1: y(k.lo), y2: y(k.hi), stroke: c.cap, 'stroke-width': small ? 12 : 16,
        'stroke-linecap': 'round'}, g);
      if (k.mid != null) el('line', {x1: cx - 11, x2: cx + 11, y1: y(k.mid), y2: y(k.mid), stroke: c.captext, 'stroke-width': 2.5}, g);
      txt(g, cx, y(k.hi) - 12, k.hi + '%', {'text-anchor': 'middle', 'font-size': 12, 'font-family': c.mono, fill: c.captext});
      txt(g, cx, y(k.lo) + 22, k.lo + '%', {'text-anchor': 'middle', 'font-size': 12, 'font-family': c.mono, fill: c.captext});
      bindTip(bar, tip, box, '<b>' + k.name + ' forecast ' + k.l3 + '</b><br>' + k.lo + '% to ' + k.hi + '%' +
        (k.mid != null ? ' (reference case ' + k.mid + '%)' : '') + '<br>Unit: ' + k.unit + '<br>' + k.tipsrc);
    }
  });
  // Callout for actual 2024, quoting the LBNL 2025 update.
  var ax = m.l + band * 1.5, a = D.cols[1];
  el('line', {x1: ax, x2: ax, y1: y(a.v) - 30, y2: 34, stroke: c.text2, 'stroke-width': 1}, svg);
  txt(svg, m.l, 14, '2024 came in at the low end of the 2024', {'font-size': 12, fill: c.text2});
  txt(svg, m.l, 29, 'report’s range (LBNL 2025 update, p. ' + D.quotePage + ')', {'font-size': 12, fill: c.text2});
}
document.querySelectorAll('#h3-buttons button').forEach(function (b) {
  b.addEventListener('click', function () { var i = +b.dataset.i; on[i] = !on[i]; b.setAttribute('aria-pressed', on[i]); render(); }); });
onResize(render); render();
"""


def h3() -> None:
    d = pd.read_csv(CLEAN / "h3_forecasts.csv")
    act = d[d["kind"] == "actual"].sort_values("target_year")
    fc = d[d["kind"] == "forecast_range"].sort_values(["report_year", "target_year"])
    highs = fc[fc["target_year"] == 2030].sort_values("report_year")["high_pct"].tolist()
    if highs != sorted(highs):
        fail(f"H3: 2030 high ends not rising with report year {highs}; title does not hold")
    a24 = act[act["target_year"] == 2024].iloc[0]
    if a24["point_pct"] > fc[fc["report"] == "LBNL 2024"]["low_pct"].iloc[0]:
        fail("H3: 2024 actual above the LBNL 2024 low end; 'low end' annotation does not hold")
    cols = ([{"kind": "actual", "l1": "Actual", "l2": str(int(r.target_year)), "l3": "", "v": r.point_pct,
              "tipsrc": r.source_title} for r in act.itertuples()] +
            [{"kind": "range", "l1": r.report.split(" ")[0], "l2": f"{int(r.report_year)} report",
              "l3": f"for {int(r.target_year)}", "s2": f"’{int(r.report_year) % 100:02d} rpt", "s3": f"→ {int(r.target_year)}",
              "lo": r.low_pct, "hi": r.high_pct,
              "mid": None if pd.isna(r.point_pct) else r.point_pct, "unit": r.unit, "name": r.report,
              "tipsrc": r.source_title} for r in fc.itertuples()])
    quote = "This falls at the low end of the estimated range in the 2024 Report"
    data = {"cols": cols, "c": col_tokens(), "quotePage": int(a24["page"])}
    buttons = "".join(f'<button type="button" aria-pressed="true" data-i="{i}">{esc(k["name"])}</button>'
                      for i, k in enumerate(cols) if k["kind"] == "range")
    page(OUT / "h3.html",
         title="Forecasts for 2030 keep rising, even as 2024 came in at the low end",
         subtitle=("Data center share of U.S. electricity: actual values (dots) and each report’s forecast range "
                   "(bars), labelled with the report year and the year forecast. Hover for details."),
         aria="", img_role=False,
         controls=(f'<div class="controls" role="group" aria-label="Show forecast" id="h3-buttons">'
                   f'<span style="font-weight:600">Show</span>{buttons}</div>'),
         chart='<div id="h3-chart"></div>',
         notes=[f'<span class="key"><span style="color:{TEXT}">●</span> actual &nbsp; '
                f'<span style="color:{CAP}">▮</span> forecast range &nbsp; '
                f'<span style="color:{CAP_TEXT}">—</span> reference case (LBNL 2025)</span>',
                "Units differ slightly by report: LBNL uses share of U.S. electricity consumption, EPRI 2024 share "
                "of generation, EPRI 2026 share of demand.",
                f"Actual 2023 is from the 2024 LBNL report; actual 2024 is from its 2025 update, which also revised "
                f"earlier years. The update says: “{quote}” (p. {data['quotePage']})."],
         script=h_script(data, H3_JS),
         source="Sources: " + "; ".join(esc(t) for t in dict.fromkeys(d["source_title"])) +
                f". Data snapshot {d['as_of'].iloc[0]}.")


# ---------------------------------------------------------------- index
# The 8 charts built by the human in web tools. DW titles read from each published page's og:title
# (2026-11-07); Flourish pages render titles client-side, so they are described, not quoted.
EXTERNAL = [
    ("DW1", "Datawrapper", "Virginia alone has more mapped data centers than Texas and California combined",
     "https://datawrapper.dwcdn.net/1UF89/1/"),
    ("DW2", "Datawrapper", "In Virginia, one in four kilowatt-hours went to data centers",
     "https://datawrapper.dwcdn.net/VEC9a/2/"),
    ("DW3", "Datawrapper", "The big jump came in 2025; 2026 added less", "https://datawrapper.dwcdn.net/we7PO/1/"),
    ("DW4", "Datawrapper", "So who wins, and who pays?", "https://datawrapper.dwcdn.net/nwkgu/1/"),
    ("F1", "Flourish", "Donut: share of mapped data-center floor space by county (title set in Flourish)",
     "https://public.flourish.studio/visualisation/30840499/"),
    ("F2", "Flourish", "Bar chart race: trailing-4-quarter capex, 5 companies (title set in Flourish)",
     "https://public.flourish.studio/visualisation/30840369/"),
    ("F3", "Flourish", "Pictogram: Virginia data-center jobs, construction vs operations (title set in Flourish)",
     "https://public.flourish.studio/visualisation/30840415/"),
    ("F4", "Flourish", "Stacked bars: data-center share of PJM capacity charges (title set in Flourish)",
     "https://public.flourish.studio/visualisation/30840465/"),
]


def index() -> None:
    own = [("P1", "Plotly", "p1"), ("P2", "Plotly", "p2"), ("P3", "Plotly", "p3"),
           ("H1", "Custom HTML/SVG", "h1"), ("H2", "Custom HTML/SVG", "h2"), ("H3", "Custom HTML/SVG", "h3")]
    rows = []
    for i, tool, f in own:
        t = re.search(r"<title>(.*?)</title>", (OUT / f"{f}.html").read_text(encoding="utf-8")).group(1)
        rows.append((i, tool, t, f"charts/{f}.html"))
    rows += [(i, tool, esc(t), u) for i, tool, t, u in EXTERNAL]
    order = {k: n for n, k in enumerate(["DW1", "DW2", "DW3", "DW4", "F1", "F2", "F3", "F4",
                                         "P1", "P2", "P3", "H1", "H2", "H3"])}
    rows.sort(key=lambda r: order[r[0]])
    if len(rows) != 14:
        fail(f"index: {len(rows)} charts, expected 14")
    trs = "".join(f'<tr><td>{i}</td><td>{tool}</td><td>{t}</td><td><a href="{u}">{"open" if u.startswith("charts/") else "embed URL"}</a></td></tr>'
                  for i, tool, t, u in rows)
    sw = [("Background", BG), ("Text", TEXT), ("Secondary text", TEXT2), ("Gridlines, borders", GRID),
          ("Costs / who pays", COST), ("Gains / who wins", GAIN), ("Baseline, neutral series", NEUTRAL),
          ("Price caps, forecasts (lines only; text in this role uses #7A5C14)", CAP), ("De-emphasized data", MUTED)]
    def chip(h: str) -> str:
        return (f'<span style="display:inline-block;width:1.2em;height:1.2em;background:{h};'
                f'border:1px solid {TEXT2};vertical-align:middle"></span>')
    swatches = "".join(f"<tr><td>{chip(h)}</td><td>{n}</td><td><code>{h}</code></td></tr>" for n, h in sw)
    seq = " ".join(f"{chip(h)} <code>{h}</code>" for h in HERO_COLORS)
    body = ('<p>Story intro: <a href="hero.html">hero map</a> (custom HTML/SVG, no chart ID).</p>'
            f'<table><thead><tr><th>ID</th><th>Tool</th><th>Title</th><th>Link</th></tr></thead><tbody>{trs}</tbody></table>'
            f'<h2>Colors</h2><table><tbody>{swatches}</tbody></table>'
            f'<p>Sequential scale for DW1 and the hero map (breaks 1, 10, 50, 100, 200 records): {seq}</p>'
            '<h2>Fonts</h2><ul><li>Source Serif 4: titles</li><li>Source Sans 3: body text and labels</li>'
            '<li>IBM Plex Mono: numbers and source lines</li></ul>'
            '<p>Fallbacks: Georgia, Arial, Courier New. Fonts are served by Google Fonts. '
            'These fonts apply to P1–P3, H1–H3 and the hero; Datawrapper and Flourish use their own font settings.</p>'
            f'<style>table {{ border-collapse: collapse; margin: 8px 0 16px; }} td, th {{ padding: 6px 10px; '
            f'border-bottom: 1px solid {GRID}; text-align: left; vertical-align: top; }} h2 {{ font-family: {SERIF}; '
            f'font-size: 1.15rem; margin: 20px 0 4px; }} a {{ color: {NEUTRAL}; }}</style>')
    page(ROOT / "docs" / "index.html", title="Who Pays for the Cloud? Chart index",
         subtitle="All 14 charts of the IE 6600 data story, with the colors and fonts they use.",
         aria="", img_role=False, chart=body,
         source="Data and code: data/clean/ and scripts/ in this repository. "
                "IM3-derived data: © OpenStreetMap contributors, ODbL 1.0.")


# ---------------------------------------------------------------- Hero (docs/hero.html)
# Standard 11 x 8 US tile grid (layout constant, not data): state -> (col, row). Odd rows are offset
# half a tile to the right to make the hexagon tiling.
TILE_GRID = {
    "AK": (0, 0), "ME": (10, 0),
    "VT": (9, 1), "NH": (10, 1),
    "WA": (0, 2), "ID": (1, 2), "MT": (2, 2), "ND": (3, 2), "MN": (4, 2), "IL": (5, 2), "WI": (6, 2),
    "MI": (7, 2), "NY": (8, 2), "RI": (9, 2), "MA": (10, 2),
    "OR": (0, 3), "NV": (1, 3), "WY": (2, 3), "SD": (3, 3), "IA": (4, 3), "IN": (5, 3), "OH": (6, 3),
    "PA": (7, 3), "NJ": (8, 3), "CT": (9, 3),
    "CA": (0, 4), "UT": (1, 4), "CO": (2, 4), "NE": (3, 4), "MO": (4, 4), "KY": (5, 4), "WV": (6, 4),
    "VA": (7, 4), "MD": (8, 4), "DE": (9, 4),
    "AZ": (1, 5), "NM": (2, 5), "KS": (3, 5), "AR": (4, 5), "TN": (5, 5), "NC": (6, 5), "SC": (7, 5),
    "DC": (8, 5),
    "OK": (3, 6), "LA": (4, 6), "MS": (5, 6), "AL": (6, 6), "GA": (7, 6),
    "HI": (0, 7), "TX": (3, 7), "FL": (8, 7),
}
# Same 6 steps as DW1: breaks 1, 10, 50, 100, 200 (value < break -> that step).
HERO_BREAKS = [1, 10, 50, 100, 200]
HERO_COLORS = ["#E9ECEF", "#C3CED8", "#93A8BC", "#62809D", "#3C5A78", "#1E3348"]
HERO_DARK = {"#62809D", "#3C5A78", "#1E3348", COST}  # white labels on these fills


def hero_step(n: int) -> int:
    return sum(n >= b for b in HERO_BREAKS)


def hero() -> None:
    d = pd.read_csv(CLEAN / "dw1_state_counts.csv")
    counts = dict(zip(d["state"], d["facilities"].astype(int)))
    if set(counts) != set(TILE_GRID):
        fail(f"hero: states differ from tile grid: {sorted(set(counts) ^ set(TILE_GRID))}")
    w = 60.0                      # tile width (pointy-top hexagon)
    r = w / math.sqrt(3)          # circumradius
    pad = 24.0
    vw = 11.5 * w + 2 * pad
    vh = 7 * 1.5 * r + 2 * r + 2 * pad

    def pts(cx: float, cy: float, rad: float) -> str:
        return " ".join(f"{cx + rad * math.cos(math.radians(a)):.1f},{cy + rad * math.sin(math.radians(a)):.1f}"
                        for a in range(-90, 270, 60))

    tiles, ring = [], ""
    for st, (c, row) in sorted(TILE_GRID.items(), key=lambda kv: (kv[1][1], kv[1][0])):
        cx = pad + w * (c + 0.5 + 0.5 * (row % 2))
        cy = pad + r + row * 1.5 * r
        fill = COST if st == "VA" else HERO_COLORS[hero_step(counts[st])]
        ink = "#FFFFFF" if fill in HERO_DARK else TEXT
        delay = -((c + row) * 0.23) % 3.2  # negative delay: staggered, already moving on load
        tiles.append(f'<g class="t" style="animation-delay:{delay:.2f}s"><polygon points="{pts(cx, cy, r * 0.94)}" '
                     f'fill="{fill}"/><text x="{cx:.1f}" y="{cy + 7:.1f}" fill="{ink}">{st}</text></g>')
        if st == "VA":
            ring = f'<polygon class="ring" points="{pts(cx, cy, r * 0.94)}"/>'
    top = d.sort_values("facilities", ascending=False).head(5)
    aria = ("Hex tile map of the United States, one hexagon per state plus D.C., shaded by the number of "
            f"mapped data center records in the PNNL IM3 Atlas ({int(d['facilities'].sum()):,} in total). "
            "Most records: " + ", ".join(f"{s} {n}" for s, n in zip(top["state"], top["facilities"].astype(int)))
            + f". Virginia is highlighted. {int((d['facilities'] == 0).sum())} states have none.")
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data center records by state</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}">
<style>
  html, body {{ margin: 0; background: {BG}; }}
  .hero {{ max-height: 420px; overflow: hidden; display: flex; flex-direction: column; align-items: center; }}
  svg {{ display: block; width: 100%; height: auto; max-height: 392px; overflow: visible; }}
  text {{ font-family: {SANS}; font-weight: 600; font-size: 21px; text-anchor: middle; pointer-events: none; }}
  .t {{ animation: pulse 3.2s ease-in-out infinite alternate; }}
  .ring {{ fill: none; stroke: {COST}; stroke-width: 3; transform-box: fill-box; transform-origin: center;
          animation: ring 3.6s ease-out infinite; }}
  @keyframes pulse {{ from {{ opacity: .85; }} to {{ opacity: 1; }} }}
  @keyframes ring {{ 0% {{ transform: scale(1); opacity: .9; }} 100% {{ transform: scale(1.75); opacity: 0; }} }}
  @media (prefers-reduced-motion: reduce) {{ .t, .ring {{ animation: none; }} .ring {{ opacity: 0; }} }}
  .foot {{ font-family: {MONO}; font-size: 11px; color: {TEXT2}; padding: 2px 16px 8px; text-align: center; }}
</style>
</head>
<body>
<div class="hero">
<svg viewBox="0 0 {vw:.0f} {vh:.0f}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="{esc(aria)}">
{ring}
{chr(10).join(tiles)}
</svg>
<div class="foot">Data center records by state. PNNL IM3 Atlas; © OpenStreetMap contributors (ODbL)</div>
</div>
</body>
</html>
"""
    path = ROOT / "docs" / "hero.html"
    path.write_text(html, encoding="utf-8")
    log.info("wrote %s (%.0f KB)", path.relative_to(ROOT), path.stat().st_size / 1024)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p1()
    p2()
    p3()
    h1()
    h2()
    h3()
    hero()
    index()


if __name__ == "__main__":
    main()
