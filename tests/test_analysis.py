import math
import statistics

import pytest

from scp import analysis


def test_cagr_hand_value():
    assert analysis.cagr({2000: 100.0, 2002: 121.0}, 2000, 2002) == pytest.approx(10.0)


def test_loglinear_recovers_exact_growth_and_zero_width_interval():
    s = {y: 50 * 1.03 ** (y - 2000) for y in range(2000, 2016)}
    r = analysis.loglinear_trend(s, 2000, 2015)
    assert r["growth_pct_per_year"] == pytest.approx(3.0, abs=1e-9)
    assert r["ci95_low"] == pytest.approx(3.0, abs=1e-9) and r["ci95_high"] == pytest.approx(3.0, abs=1e-9)
    assert r["n_points"] == 16


def test_loglinear_excludes_years():
    s = {y: 50 * 1.03 ** (y - 2000) for y in range(2000, 2016)}
    s[2008] = 1.0  # outlier removed by exclusion
    r = analysis.loglinear_trend(s, 2000, 2015, exclude=(2008,))
    assert r["growth_pct_per_year"] == pytest.approx(3.0, abs=1e-9) and r["n_points"] == 15


def test_trend_interval_brackets_point(recomputed):
    t = recomputed["productivity_trend.json"]
    for k in ("trend_va_per_hour_excl_covid", "trend_va_per_hour_all"):
        assert t[k]["ci95_low"] < t[k]["growth_pct_per_year"] < t[k]["ci95_high"]


def test_trend_headlines(recomputed):
    t = recomputed["productivity_trend.json"]
    assert t["latest_year"] == 2025 and t["first_year_hourly"] == 2009
    assert t["va_per_man_day_equiv_latest"] == pytest.approx(18.3837 * 8, abs=1e-6)
    assert t["construction_vs_total_per_hour_pct_latest"] == pytest.approx(100 * 18.3837 / 64.3139, abs=1e-6)
    assert t["covid_2020_drop_pct"] == pytest.approx(100 * (26180.7519 / 43064.7622 - 1), abs=1e-6)
    assert t["implied_hours_per_worker_latest"] == pytest.approx(40654.8518 / 18.3837, abs=1e-4)
    assert t["cagr_va_per_hour_2019_latest_pct"] == pytest.approx(100 * ((18.3837 / 18.421) ** (1 / 6) - 1), abs=1e-6)


def test_dfma_correlation_matches_statistics_module(recomputed):
    d = recomputed["dfma_evidence.json"]
    xs = [p["adoption_pct"] for p in d["adoption_points"]]
    ys = [p["va_per_hour"] for p in d["adoption_points"]]
    assert d["pearson_r"] == pytest.approx(statistics.correlation(xs, ys), abs=1e-6)
    assert abs(d["pearson_r"]) < d["r_critical_5pct_df2"]
    assert d["n_points"] == 4 and d["adoption_change_pts"] == 37
    assert d["va_per_hour_change_pct_same_years"] == pytest.approx(100 * (17.9345 / 18.421 - 1), abs=1e-6)


def test_demand_shares(recomputed):
    d = recomputed["dfma_evidence.json"]
    assert d["building_share_of_contracts_latest_pct"] == pytest.approx(100 * 41366.5 / 50656.1, abs=1e-6)
    assert d["building_share_of_payments_latest_pct"] == pytest.approx(100 * 31552.7 / 41865.6, abs=1e-6)
    assert d["contracts_awarded_growth_2019_latest_pct"] == pytest.approx(100 * (50656.1 / 33523.8 - 1), abs=1e-6)
    assert d["cmp_2019_to_2020_pct"] == pytest.approx(100 * (311100 / 370100 - 1), abs=1e-6)
    assert math.isclose(d["cmp_latest"], 415000)
