# Google Sites embeds (15, in story order)

How to paste:
- **iframe snippets:** in Google Sites use **Insert → Embed → Embed code**, paste the snippet, then drag the box to the height shown.
- **Datawrapper and GitHub Pages charts:** you can also use **Embed → By URL** with the `src` URL alone.
- **Flourish:** paste the code unchanged under **Embed code**. Flourish's `embed.js` sizes the chart, but you still set the Sites box height by hand.

Starting heights:
- **GitHub Pages pages:** the page height measured in headless Edge at 900 px width, plus about 20 px, rounded up. At a 380 px phone width the same pages are 120–200 px taller (in parentheses).
- **Datawrapper:** placeholders marked **adjust**. Check each one in the Sites preview.

GitHub Pages base: https://scofe-c.github.io/who-pays-for-the-cloud/

---

## 0. Hero (custom HTML/SVG)
Height 420 px (phone: map ≈ 300 px)
```html
<iframe src="https://scofe-c.github.io/who-pays-for-the-cloud/hero.html" title="Data center records by state" style="width:100%;height:420px;border:0" loading="lazy"></iframe>
```

## Act 1: Scale

### DW1 (Datawrapper)
Height 520 px, **adjust**
```html
<iframe src="https://datawrapper.dwcdn.net/1UF89/1/" title="Virginia alone has more mapped data centers than Texas and California combined" style="width:100%;height:520px;border:0" loading="lazy"></iframe>
```

### DW2 (Datawrapper)
Height 560 px, **adjust**
```html
<iframe src="https://datawrapper.dwcdn.net/VEC9a/2/" title="In Virginia, one in four kilowatt-hours went to data centers" style="width:100%;height:560px;border:0" loading="lazy"></iframe>
```

### F1 (Flourish)
Suggested box height ≈ 550 px
```html
<div class="flourish-embed flourish-chart" data-src="visualisation/30840499"><script src="https://public.flourish.studio/resources/embed.js"></script><noscript><img src="https://public.flourish.studio/visualisation/30840499/thumbnail" width="100%" alt="chart visualization" /></noscript></div>
```

## Act 2: Power

### H3 (custom HTML/SVG)
Height 840 px (phone 1,020)
```html
<iframe src="https://scofe-c.github.io/who-pays-for-the-cloud/charts/h3.html" title="Forecasts for 2030 keep rising, even as 2024 came in at the low end" style="width:100%;height:840px;border:0" loading="lazy"></iframe>
```

### P3 (Plotly)
Height 590 px (phone 700)
```html
<iframe src="https://scofe-c.github.io/who-pays-for-the-cloud/charts/p3.html" title="Global data-center electricity use nearly doubles by 2030" style="width:100%;height:590px;border:0" loading="lazy"></iframe>
```

## Act 3: Money

### P2 (Plotly)
Height 800 px (phone 960)
```html
<iframe src="https://scofe-c.github.io/who-pays-for-the-cloud/charts/p2.html" title="Data-center construction now outspends general office buildings" style="width:100%;height:800px;border:0" loading="lazy"></iframe>
```

### F2 (Flourish)
Suggested box height ≈ 600 px
```html
<div class="flourish-embed flourish-bar-chart-race" data-src="visualisation/30840369"><script src="https://public.flourish.studio/resources/embed.js"></script><noscript><img src="https://public.flourish.studio/visualisation/30840369/thumbnail" width="100%" alt="bar-chart-race visualization" /></noscript></div>
```

### F3 (Flourish)
Suggested box height ≈ 500 px
```html
<div class="flourish-embed flourish-pictogram" data-src="visualisation/30840415"><script src="https://public.flourish.studio/resources/embed.js"></script><noscript><img src="https://public.flourish.studio/visualisation/30840415/thumbnail" width="100%" alt="pictogram visualization" /></noscript></div>
```

## Act 4: Costs

### H1 (custom HTML/SVG)
Height 760 px (phone 860)
```html
<iframe src="https://scofe-c.github.io/who-pays-for-the-cloud/charts/h1.html" title="Three auctions in a row hit the ceiling" style="width:100%;height:760px;border:0" loading="lazy"></iframe>
```

### F4 (Flourish)
Suggested box height ≈ 450 px
```html
<div class="flourish-embed flourish-chart" data-src="visualisation/30840465"><script src="https://public.flourish.studio/resources/embed.js"></script><noscript><img src="https://public.flourish.studio/visualisation/30840465/thumbnail" width="100%" alt="chart visualization" /></noscript></div>
```

### DW3 (Datawrapper)
Height 480 px, **adjust**
```html
<iframe src="https://datawrapper.dwcdn.net/we7PO/1/" title="The big jump came in 2025; 2026 added less" style="width:100%;height:480px;border:0" loading="lazy"></iframe>
```

### H2 (custom HTML/SVG)
Height 780 px (phone 950)
```html
<iframe src="https://scofe-c.github.io/who-pays-for-the-cloud/charts/h2.html" title="The tax break grew faster than the new tax can recoup" style="width:100%;height:780px;border:0" loading="lazy"></iframe>
```

## Counterpoint

### P1 (Plotly)
Height 770 px (phone 900)
```html
<iframe src="https://scofe-c.github.io/who-pays-for-the-cloud/charts/p1.html" title="Growth alone didn’t raise prices" style="width:100%;height:770px;border:0" loading="lazy"></iframe>
```

## Ending

### DW4 (Datawrapper)
Height 700 px, **adjust** (searchable table, 9 rows)
```html
<iframe src="https://datawrapper.dwcdn.net/nwkgu/1/" title="So who wins, and who pays?" style="width:100%;height:700px;border:0" loading="lazy"></iframe>
```

---

## Notes
- **Titles:** Datawrapper titles were read from each published page (og:title, 2026-11-07). If you republish a Datawrapper chart, its URL version (`/1/`, `/2/`) changes. Update the `src` or use the version-less URL Datawrapper shows.
- **Fixed heights:** a Google Sites embed box doesn't resize itself. The phone heights above show how much taller the pages get at 380 px. Pick a height that works on both, or accept some inner scrolling on phones.
- **Stable URLs:** the GitHub Pages URLs stay the same as long as the file names in `docs/` don't change (DEPLOY.md: never rename after embedding).
