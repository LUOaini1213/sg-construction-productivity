import json
import re

import pytest

from conftest import ROOT
from scp import dashboard

HTML = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")


def _json_block(block_id):
    m = re.search(rf'<script type="application/json" id="{re.escape(block_id)}">(.*?)</script>', HTML, re.S)
    assert m, block_id
    return json.loads(m.group(1))


def test_committed_dashboard_equals_render_of_recomputed(recomputed):
    assert HTML == dashboard.render(recomputed)


def test_kpi_values_reconcile(recomputed):
    vals = _json_block("kpi-values")
    t, d = recomputed["productivity_trend.json"], recomputed["dfma_evidence.json"]
    b = recomputed["model_base.json"]["scenarios"]
    expected = {
        "va_hour": t["va_per_hour_latest"],
        "va_hour_share": t["construction_vs_total_per_hour_pct_latest"],
        "trend": t["trend_va_per_hour_excl_covid"]["growth_pct_per_year"],
        "dfma": 68,
        "ppvc_mp": b["ppvc"]["manpower_saving_pct"],
        "ppvc_days": b["ppvc"]["duration_saving_days"],
    }
    assert vals.keys() == expected.keys()
    for k, v in expected.items():
        assert vals[k] == pytest.approx(v, abs=1e-9), k


def test_kpi_card_text_matches_value():
    vals = _json_block("kpi-values")
    for k in vals:
        m = re.search(rf'data-kpi="{k}"><div class="v">([^<]+)</div>', HTML)
        shown = m.group(1)
        num = float(shown.rstrip("%").replace(",", ""))
        decimals = len(shown.rstrip("%").split(".")[1]) if "." in shown else 0
        assert num == pytest.approx(vals[k], abs=0.5 * 10 ** -decimals + 1e-12), k


def test_plotted_series_reconcile(recomputed):
    t, d = recomputed["productivity_trend.json"], recomputed["dfma_evidence.json"]
    fig = _json_block("fig_va_hour-json")
    assert fig["data"][0]["y"] == t["series"]["va_per_hour"]
    assert fig["data"][1]["y"] == t["series"]["va_per_hour_total"]
    assert fig["data"][0]["x"] == list(range(2009, 2026))
    fig = _json_block("fig_dfma-json")
    assert fig["data"][0]["x"] == [p["adoption_pct"] for p in d["adoption_points"]]
    assert fig["data"][0]["y"] == [p["va_per_hour"] for p in d["adoption_points"]]
    fig = _json_block("fig_demand-json")
    assert fig["data"][0]["y"] == d["series"]["contracts_awarded"]
    assert fig["data"][1]["y"] == d["series"]["progress_payments"]


def test_plotted_model_values_reconcile(recomputed):
    b = recomputed["model_base.json"]["scenarios"]
    for fid, metric in (("fig_manday", "site_man_days"), ("fig_duration", "duration_days"),
                        ("fig_prod", "site_productivity_m2_per_md")):
        fig = _json_block(fid + "-json")
        assert fig["data"][0]["y"] == [b[s][metric] for s in dashboard.LABEL], fid
    lob = recomputed["model_lob.json"]
    fig = _json_block("fig_lob-json")
    starts = [tr["x"] for tr in fig["data"]]
    assert starts == [row for s in ("conventional", "ppvc") for row in lob[s]["start"]]


def test_tornado_values_reconcile(recomputed):
    rows = {r["param"]: r for r in recomputed["model_sensitivity.json"]["rows"]
            if r["metric"] == "manpower_saving_pct"}
    fig = _json_block("fig_tornado-json")
    assert len(fig["data"][1]["y"]) == 10
    for trace, key in ((fig["data"][0], "at_low"), (fig["data"][1], "at_high")):
        for y, x in zip(trace["y"], trace["x"]):
            assert x == pytest.approx(rows[y][key] - rows[y]["base"], abs=1e-9)


def test_no_dual_axis_and_required_disclaimer():
    assert "yaxis2" not in HTML
    assert "Personal desk study on public data; not a BCA study." in HTML
