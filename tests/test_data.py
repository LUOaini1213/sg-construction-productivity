import hashlib
import json

from conftest import ROOT
from scp import data


def test_manifest_hashes_match_committed_files():
    m = json.loads((ROOT / "data/raw/manifest.json").read_text(encoding="utf-8"))
    assert m["licence"].startswith("Singapore Open Data Licence")
    assert len(m["datasets"]) == 4
    for name, d in m["datasets"].items():
        body = (ROOT / f"data/raw/{name}.csv").read_bytes()
        assert hashlib.sha256(body).hexdigest() == d["sha256"], name


def test_known_values_parse():
    assert data.construction_va_per_hour()[2025] == 18.3837
    assert data.construction_va_per_hour()[2009] == 15.5567
    assert data.total_va_per_hour()[2025] == 64.3139
    assert data.construction_va_per_worker()[2020] == 26180.7519
    assert data.cmp_work_permits()[2019] == 370100.0  # quoted "370,100" in the CSV
    assert data.cmp_work_permits()[2022] == 415000.0


def test_na_values_are_dropped():
    w = data.construction_va_per_worker()
    assert 1983 not in w and 1991 in w


def test_construction_row_is_the_industry_not_a_subrow():
    # the first "Construction" row sits under Goods Producing Industries
    w = data.singstat_wide(ROOT / "data/raw/va_per_worker_chained_annual.csv")
    assert w["Construction"][2025] == 40654.8518


def test_contract_blocks():
    cp = data.contracts_and_payments()
    ca = cp["Contracts Awarded - Total Public & Private Sector"]
    assert ca["Total"][2025] == 50656.1
    assert ca["Building Work"][2025] == 41366.5
    assert abs(ca["Building Work"][2025] + ca["Civil Engineering Work"][2025] - ca["Total"][2025]) < 0.2
    pp = cp["Progress Payments Certified - Total Public & Private Sector"]
    assert pp["Total"][2025] == 41865.6


def test_bca_figures_are_cited_single_figures():
    figs = data.bca_figures()
    ids = [f["id"] for f in figs]
    assert len(ids) == len(set(ids))
    for f in figs:
        assert f["url"].startswith("https://www1.bca.gov.sg/"), f["id"]
        assert f["location"] and f["access"] and f["what"]
        assert isinstance(f["value"], (int, float))
    adoption = sorted((f["ref_year"], f["value"]) for f in figs if f["kind"] == "adoption")
    assert adoption == [(2019, 31), (2022, 44), (2023, 61), (2024, 68)]


def test_singstat_wide_first_duplicate_name_wins(tmp_path):
    p = tmp_path / "t.csv"
    p.write_text('DataSeries,2025,2024\nTotal,10,9\n    Others,1,na\n        Others,2,3\n', encoding="utf-8")
    t = data.singstat_wide(p)
    assert t["Total"] == {2025: 10.0, 2024: 9.0}
    assert t["Others"] == {2025: 1.0}
