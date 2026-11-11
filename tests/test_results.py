from conftest import ROOT
from scp.results import compute_all, dumps


def test_committed_results_equal_recomputed(recomputed):
    for name, obj in recomputed.items():
        assert (ROOT / "results" / name).read_text(encoding="utf-8") == dumps(obj), name


def test_compute_is_deterministic(recomputed):
    assert compute_all() == recomputed


def test_mutation_report_present(committed):
    m = committed["mutation.json"]
    assert m["first_run"]["total"] >= 20 and m["final"]["total"] >= 20
    assert 0 <= m["final"]["killed"] <= m["final"]["total"]
