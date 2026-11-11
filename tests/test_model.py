import pytest

from scp import data, model


@pytest.fixture(scope="module")
def params():
    return data.model_params()


@pytest.fixture(scope="module")
def base(params):
    return model.compare(model.values(params))


def test_lob_equal_trades_hand_case():
    r = model.line_of_balance([("a", 2), ("b", 2)], 3, 0)
    assert r["start"] == [[0, 2, 4], [2, 4, 6]]
    assert r["end"] == 8  # (floors + trades - 1) * d


def test_lob_bottleneck_and_buffer_hand_case():
    r = model.line_of_balance([("a", 1), ("b", 3)], 3, 1)
    assert r["start"][1] == [2, 5, 8]
    assert r["end"] == 11


def test_lob_ready_times_delay_first_trade():
    r = model.line_of_balance([("a", 1)], 2, 0, first_trade_ready=[5, 5.5])
    assert r["start"][0] == [5, 6] and r["end"] == 7


def test_lob_no_overlap_on_any_floor(base):
    for scen in model.SCENARIOS:
        lob = base[scen]["lob"]
        for i in range(1, len(lob["trades"])):
            for f in range(len(lob["start"][0])):
                assert lob["start"][i][f] >= lob["finish"][i - 1][f]
        for i in range(len(lob["trades"])):
            for f in range(1, len(lob["start"][0])):
                assert lob["start"][i][f] >= lob["finish"][i][f - 1]


def test_conventional_hand_values(base):
    c = base["conventional"]
    assert c["gfa_m2"] == 16 * 650
    assert c["site_man_days"] == pytest.approx(2.0 * 16 * 650)
    assert c["superstructure_days"] == 15 + 8 * 16  # architectural trade is the bottleneck
    assert c["duration_days"] == 90 + 143 + 60
    assert c["takt_days"] == 8


def test_precast_and_prefab_mep_hand_values(base):
    gfa = 16 * 650
    assert base["precast"]["site_man_days"] == pytest.approx(2.0 * gfa * (1 - 0.35 * 0.35))
    assert base["precast_prefab_mep"]["site_man_days"] == pytest.approx(2.0 * gfa * (1 - 0.35 * 0.35 - 0.15 * 0.40))
    assert base["precast"]["lob"]["finish"][0][0] == pytest.approx(7 * 0.7)
    mep = base["precast_prefab_mep"]["lob"]
    assert mep["finish"][1][0] - mep["start"][1][0] == pytest.approx(6 * 0.6)


def test_ppvc_hand_man_days(base):
    gfa = 16 * 650
    expected = 2.0 * gfa * (0.20 + 0.35 * 0.45 + 0.15 * 0.50 + 0.30 * 0.35) + 6 * 16 * 16
    assert base["ppvc"]["site_man_days"] == pytest.approx(expected)
    assert base["ppvc"]["manpower_saving_pct"] == pytest.approx(100 * (1 - expected / (2.0 * gfa)))
    assert base["ppvc"]["productivity_ratio"] == pytest.approx(2.0 * gfa / expected)
    assert base["ppvc"]["duration_days"] == pytest.approx(90 + base["ppvc"]["superstructure_days"] + 60)


def test_ppvc_install_rate_from_crane(base):
    lob = base["ppvc"]["lob"]
    assert lob["finish"][0][0] - lob["start"][0][0] == pytest.approx(16 / 8)
    assert lob["start"][0][0] == 0  # 60-day factory lead: first floor of modules is ready


def test_factory_becomes_constraint_without_lead(params):
    p = model.values(params)
    p["factory_lead_days"] = 0
    r = model.scenario(p, "ppvc")
    assert r["lob"]["start"][0][-1] == pytest.approx(16 * 16 / 4)
    assert r["lob"]["start"][0][0] == pytest.approx(16 / 4)


def test_non_bottleneck_speed_up_barely_shortens_duration(base):
    pc, c = base["precast"], base["conventional"]
    assert pc["manpower_saving_pct"] > 10
    assert 0 < pc["duration_saving_days"] < 0.01 * c["duration_days"]


def test_relative_metrics_zero_for_conventional(base):
    c = base["conventional"]
    assert c["manpower_saving_pct"] == 0 and c["duration_saving_days"] == 0 and c["productivity_ratio"] == 1


def test_duration_months_conversion(base):
    p = base["ppvc"]
    assert p["duration_saving_months"] == pytest.approx(p["duration_saving_days"] * 12 / 365.25)


def test_labour_shares_must_leave_room_for_architecture(params):
    p = model.values(params)
    p["share_structure"] = 0.7
    with pytest.raises(ValueError):
        model.scenario(p, "conventional")


def test_every_parameter_is_labelled_and_swept(params):
    cited = {f["id"]: f for f in data.bca_figures()}
    for k, s in params["params"].items():
        assert s["kind"] in ("assumption", "cited"), k
        assert s["low"] <= s["value"] <= s["high"], k
        assert s["low"] < s["high"], k
        assert s["unit"], k
        if "cite" in s:
            assert s["cite"] in cited
    assert params["params"]["prefab_mep_time_cut"]["high"] == cited["prefab_mep_time_upper"]["value"] / 100
    for c in params["checks_against_cited"]:
        for key in ("cited_low", "cited_high"):
            if key in c:
                assert c[key] in cited


def test_sensitivity_covers_every_parameter(params, recomputed):
    rows = recomputed["model_sensitivity.json"]["rows"]
    assert {r["param"] for r in rows} == set(params["params"])
    assert len(rows) == 3 * len(params["params"])
    swing = {(r["param"], r["metric"]): r for r in rows}
    r = swing[("ppvc_structure_labour_cut", "manpower_saving_pct")]
    assert r["at_high"] > r["base"] > r["at_low"]
    assert r["swing"] == pytest.approx(r["at_high"] - r["at_low"])
    top = recomputed["model_sensitivity.json"]["top3_by_swing"]["manpower_saving_pct"]
    assert top[0] == max((x for x in rows if x["metric"] == "manpower_saving_pct"), key=lambda x: x["swing"])["param"]


def test_monte_carlo_ordered_and_reproducible(params, recomputed):
    mc = recomputed["model_montecarlo.json"]
    assert mc["samples"] == params["monte_carlo"]["samples"]
    for m in model.HEADLINE:
        assert mc[m]["p5"] < mc[m]["p50"] < mc[m]["p95"]
    small = dict(params, monte_carlo=dict(params["monte_carlo"], samples=50))
    assert model.monte_carlo(small) == model.monte_carlo(small)


def test_quantile():
    assert model._quantile([0.0, 10.0], 0.5) == 5.0
    assert model._quantile([1.0, 2.0, 3.0], 0.0) == 1.0 and model._quantile([1.0, 2.0, 3.0], 1.0) == 3.0
    assert model._quantile([0.0, 10.0, 20.0, 30.0], 0.25) == pytest.approx(7.5)


def test_checks_against_cited(recomputed):
    checks = {c["metric"]: c for c in recomputed["model_base.json"]["checks_against_cited"]}
    m = checks["ppvc_manpower_saving_pct"]
    assert (m["cited_low"], m["cited_high"]) == (20, 40)
    assert m["within_cited_range"] == (m["cited_low"] <= m["model"] <= m["cited_high"])
    f = checks["ppvc_time_per_floor_cut_pct"]
    assert f["cited_high"] == 30 and f["within_cited_range"] == (f["model"] <= f["cited_high"])


def test_bottleneck_and_factory_pace(base):
    assert base["conventional"]["bottleneck_trade"] == "arch"
    assert base["ppvc"]["bottleneck_trade"] == "finishing"
    assert base["ppvc"]["factory_days_per_floor"] == pytest.approx(16 / 4)
    assert base["conventional"]["factory_days_per_floor"] is None
    assert base["ppvc"]["factory_days_per_floor"] < base["ppvc"]["takt_days"]


def test_factory_slower_than_finishing_lengthens_programme(params):
    p = model.values(params)
    p["factory_lead_days"], p["factory_modules_per_day"] = 0, 2  # 8 days per floor of modules
    slow = model.scenario(p, "ppvc")
    assert slow["superstructure_days"] > model.scenario(model.values(params), "ppvc")["superstructure_days"]
