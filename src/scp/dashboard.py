"""Static Plotly HTML dashboard built from results/*.json.

Every number shown is taken from the result dicts; tests/test_dashboard.py re-parses the HTML and
reconciles it against numbers recomputed from data/ and params/.
"""
from __future__ import annotations

import html
import json

import plotly.graph_objects as go
from plotly.utils import PlotlyJSONEncoder

PLOTLY_JS = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"
BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#8a8984"
LABEL = {"conventional": "Conventional", "precast": "Precast frame",
         "precast_prefab_mep": "Precast + prefab MEP", "ppvc": "PPVC"}


def kpis(res: dict) -> list[dict]:
    t, d = res["productivity_trend.json"], res["dfma_evidence.json"]
    b = res["model_base.json"]["scenarios"]
    mc = res["model_montecarlo.json"]
    tr = t["trend_va_per_hour_excl_covid"]
    return [
        {"id": "va_hour", "label": f"Construction VA per actual hour, {t['latest_year']} (chained 2015 S$)",
         "value": t["va_per_hour_latest"], "fmt": "{:.2f}"},
        {"id": "va_hour_share", "label": "Construction VA per hour as % of whole economy",
         "value": t["construction_vs_total_per_hour_pct_latest"], "fmt": "{:.1f}%"},
        {"id": "trend", "label": f"Trend growth {tr['years']} excl. 2020-21, % a year (95% CI "
                                 f"{tr['ci95_low']:.2f} to {tr['ci95_high']:.2f})",
         "value": tr["growth_pct_per_year"], "fmt": "{:.2f}"},
        {"id": "dfma", "label": f"DfMA adoption, {d['adoption_last_year']} (BCA, by GFA)",
         "value": d["adoption_points"][-1]["adoption_pct"], "fmt": "{:.0f}%"},
        {"id": "ppvc_mp", "label": "Model: PPVC site manpower saving (base; MC p5-p95 "
                                   f"{mc['manpower_saving_pct']['p5']:.1f}-{mc['manpower_saving_pct']['p95']:.1f}%)",
         "value": b["ppvc"]["manpower_saving_pct"], "fmt": "{:.1f}%"},
        {"id": "ppvc_days", "label": "Model: PPVC duration saving, days (base; MC p5-p95 "
                                     f"{mc['duration_saving_days']['p5']:.0f}-{mc['duration_saving_days']['p95']:.0f})",
         "value": b["ppvc"]["duration_saving_days"], "fmt": "{:.0f}"},
    ]


def figures(res: dict) -> dict[str, go.Figure]:
    t, d = res["productivity_trend.json"], res["dfma_evidence.json"]
    b = res["model_base.json"]["scenarios"]
    s = t["series"]
    figs = {}

    f = go.Figure()
    f.add_scatter(x=s["year"], y=s["va_per_hour"], name="Construction", line={"color": BLUE, "width": 2})
    f.add_scatter(x=s["year"], y=s["va_per_hour_total"], name="Whole economy", line={"color": GREY, "width": 2})
    f.update_layout(title="Value added per actual hour worked, chained (2015) S$", yaxis_title="S$ per hour")
    figs["fig_va_hour"] = f

    pts = d["adoption_points"]
    f = go.Figure()
    f.add_scatter(x=[p["adoption_pct"] for p in pts], y=[p["va_per_hour"] for p in pts],
                  mode="markers+text", text=[str(p["year"]) for p in pts], textposition="top center",
                  marker={"color": BLUE, "size": 10}, name="Year", showlegend=False)
    f.update_layout(title=f"DfMA adoption vs construction VA per hour (n = {d['n_points']}, "
                          f"r = {d['pearson_r']:.2f})",
                    xaxis_title="DfMA adoption, % (BCA single figures)", yaxis_title="S$ per hour")
    figs["fig_dfma"] = f

    s2 = d["series"]
    f = go.Figure()
    f.add_scatter(x=s2["year"], y=s2["contracts_awarded"], name="Contracts awarded", line={"color": BLUE, "width": 2})
    f.add_scatter(x=s2["year"], y=s2["progress_payments"], name="Progress payments certified",
                  line={"color": ORANGE, "width": 2})
    f.update_layout(title="Construction demand and output, S$ million (current prices)", yaxis_title="S$ million")
    figs["fig_demand"] = f

    names = list(LABEL)
    for key, metric, title in (("fig_manday", "site_man_days", "Model: site man-days"),
                               ("fig_duration", "duration_days", "Model: duration, days"),
                               ("fig_prod", "site_productivity_m2_per_md", "Model: site productivity, m2 GFA per man-day")):
        f = go.Figure()
        f.add_bar(x=[LABEL[n] for n in names], y=[b[n][metric] for n in names], marker_color=BLUE, name=title,
                  showlegend=False)
        f.update_layout(title=title)
        figs[key] = f

    rows = [r for r in res["model_sensitivity.json"]["rows"] if r["metric"] == "manpower_saving_pct"]
    rows = sorted(rows, key=lambda r: r["swing"])[-10:]
    f = go.Figure()
    f.add_bar(y=[r["param"] for r in rows], x=[r["at_low"] - r["base"] for r in rows], orientation="h",
              name="Parameter at low bound", marker_color=BLUE)
    f.add_bar(y=[r["param"] for r in rows], x=[r["at_high"] - r["base"] for r in rows], orientation="h",
              name="Parameter at high bound", marker_color=ORANGE)
    f.update_layout(barmode="overlay", title="Sensitivity: change in PPVC manpower saving, percentage points",
                    xaxis_title="points vs base")
    figs["fig_tornado"] = f

    lob = res["model_lob.json"]
    f = go.Figure()
    colors = {"conventional": BLUE, "ppvc": ORANGE}
    for scen, sch in lob.items():
        floors = list(range(1, len(sch["start"][0]) + 1))
        for i, trade in enumerate(sch["trades"]):
            f.add_scatter(x=sch["start"][i], y=floors, mode="lines",
                          line={"color": colors[scen], "width": 2, "dash": "solid" if i == 0 else "dot"},
                          name=f"{LABEL[scen]}: {trade} start")
    f.update_layout(title="Line of balance: start day of each trade on each floor (superstructure)",
                    xaxis_title="day from first superstructure activity", yaxis_title="floor")
    figs["fig_lob"] = f

    for fig in figs.values():
        fig.update_layout(template="plotly_white", font={"family": "system-ui, sans-serif", "size": 13},
                          margin={"l": 60, "r": 20, "t": 60, "b": 50}, hovermode="closest",
                          title_font_size=14, legend={"orientation": "h", "y": -0.25, "x": 0})
    return figs


WIDE = ("fig_tornado", "fig_lob")

CSS = """
:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--card:#ffffff;--line:#e4e3df}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--card:#232322;--line:#3a3a38}}
:root[data-theme="dark"]{--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--card:#232322;--line:#3a3a38}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}
.kpi .v{font-size:28px;font-weight:600}.kpi .l{color:var(--ink2);font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px;margin-top:12px}
.fig.wide{grid-column:1/-1;min-height:460px}
.fig{background:#fff;border:1px solid var(--line);border-radius:8px;min-height:360px}
p.note{color:var(--ink2);font-size:13px}
"""


def render(res: dict) -> str:
    k = kpis(res)
    figs = figures(res)
    cards = "".join(
        f'<div class="kpi" data-kpi="{x["id"]}"><div class="v">{html.escape(x["fmt"].format(x["value"]))}</div>'
        f'<div class="l">{html.escape(x["label"])}</div></div>' for x in k)
    blocks, scripts = [], []
    for fid, fig in figs.items():
        wide = " wide" if fid in WIDE else ""
        blocks.append(f'<div class="fig{wide}" id="{fid}"></div>')
        payload = json.dumps(fig.to_plotly_json(), cls=PlotlyJSONEncoder, sort_keys=True)
        scripts.append(f'<script type="application/json" id="{fid}-json">{payload}</script>')
    values = json.dumps({x["id"]: x["value"] for x in k}, sort_keys=True)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SG Construction Productivity</title><style>{CSS}</style>
<script src="{PLOTLY_JS}"></script></head>
<body><main>
<h1>Singapore construction productivity and DfMA</h1>
<p class="note">Personal desk study on public data; not a BCA study. Static Plotly dashboard generated by
scripts/build_dashboard.py from results/*.json. Model panels show an illustrative hypothetical building whose
parameters are labelled assumptions (params/model.json); they are not measurements.</p>
<div class="kpis">{cards}</div>
<div class="grid">{''.join(blocks)}</div>
<script type="application/json" id="kpi-values">{values}</script>
{''.join(scripts)}
<script>
for (const el of document.querySelectorAll('.fig')) {{
  const spec = JSON.parse(document.getElementById(el.id + '-json').textContent);
  if (window.Plotly) Plotly.newPlot(el, spec.data, spec.layout, {{responsive: true, displaylogo: false}});
  else el.textContent = 'Plotly.js could not be loaded; the figure data is embedded in this page as JSON.';
}}
</script>
</main></body></html>
"""
