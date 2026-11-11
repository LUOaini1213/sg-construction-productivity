"""Mutation check: plant one bug at a time, run the test suite, count how many bugs a test catches.

Writes results/mutation.json. The first recorded run is kept as "first_run"; every run is appended to
"history" and the latest becomes "final". Source files are restored after each mutant.
"""
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = "src/scp/"

MUTANTS = [
    ("data_strip_na", S + "data.py", 'if s in ("", "na", "-"):', 'if s in ("", "-"):'),
    ("data_first_row_wins", S + "data.py", "        if name in out:\n            continue\n", ""),
    ("data_wrong_permit_type", S + "data.py", '== "construction_marine_process"', '== "foreign_domestic_worker"'),
    ("data_comma_strip", S + "data.py", '.replace(",", "")', '.replace(",", ".")'),
    ("trend_cagr_exponent", S + "analysis.py", "(1 / (y1 - y0))", "(1 / (y1 - y0 + 1))"),
    ("trend_ci_index", S + "analysis.py", "int(0.975 * n_boot) - 1", "int(0.995 * n_boot) - 1"),
    ("trend_no_exclusion", S + "analysis.py", "and y not in exclude", ""),
    ("trend_man_day_hours", S + "analysis.py", "HOURS_PER_MAN_DAY = 8", "HOURS_PER_MAN_DAY = 7.5"),
    ("trend_share_inverted", S + "analysis.py", "100 * h[last] / th[last]", "100 * th[last] / h[last]"),
    ("dfma_r_no_sqrt", S + "analysis.py", "/ math.sqrt(sum(", "/ (sum("),
    ("dfma_building_share_payments", S + "analysis.py",
     '100 * pp["Building Work"][last] / pp["Total"][last]', '100 * ca["Building Work"][last] / pp["Total"][last]'),
    ("lob_no_buffer", S + "model.py", "finish[i - 1][f] + buffer", "finish[i - 1][f]"),
    ("lob_no_floor_sequence", S + "model.py", "            if f > 0:\n                s = max(s, finish[i][f - 1])\n", ""),
    ("lob_ignore_ready", S + "model.py", "s = max(s, first_trade_ready[f])", "s = s"),
    ("lob_end_wrong_floor", S + "model.py", '"end": finish[-1][-1]', '"end": finish[-1][0]'),
    ("model_arch_share", S + "model.py", 'arch = 1.0 - p["share_substructure"]', 'arch = 1.1 - p["share_substructure"]'),
    ("model_precast_cycle", S + "model.py", 's * (1 - p["precast_cycle_cut"])), ("mep", m), ("arch", a)]',
     's * (1 + p["precast_cycle_cut"])), ("mep", m), ("arch", a)]'),
    ("model_install_labour_dropped", S + "model.py", 'extra_md = p["install_md_per_module"] * mods * floors',
     'extra_md = p["install_md_per_module"] * mods'),
    ("model_factory_rate", S + "model.py", "(f + 1) * mods / rate", "f * mods / rate"),
    ("model_tail_dropped", S + "model.py", '+ lob["end"] + p["tail_days"]', '+ lob["end"]'),
    ("model_saving_sign", S + "model.py", "100 * (1 - r[\"site_man_days\"] / c[\"site_man_days\"])",
     "100 * (r[\"site_man_days\"] / c[\"site_man_days\"] - 1)"),
    ("model_months", S + "model.py", "(365.25 / 12)", "30"),
    ("model_sens_same_bound", S + "model.py", 'lo[k], hi[k] = spec["low"], spec["high"]', 'lo[k], hi[k] = spec["low"], spec["low"]'),
    ("model_mc_mode", S + "model.py", 'rng.triangular(s["low"], s["high"], s["value"])', 'rng.uniform(s["low"], s["high"])'),
    ("model_quantile", S + "model.py", "pos = (len(xs) - 1) * q", "pos = len(xs) * q * 0.99"),
    ("results_check_bounds", S + "results.py", "(lo is None or val >= lo) and (hi is None or val <= hi)",
     "(lo is None or val >= lo)"),
    ("results_rounding", S + "results.py", "def _round(x, nd=6):", "def _round(x, nd=3):"),
    ("dash_kpi_wrong_value", S + "dashboard.py", '"value": b["ppvc"]["manpower_saving_pct"]', '"value": b["precast"]["manpower_saving_pct"]'),
    ("dash_series_swapped", S + "dashboard.py", 'f.add_scatter(x=s["year"], y=s["va_per_hour"], name="Construction"',
     'f.add_scatter(x=s["year"], y=s["va_per_hour_total"], name="Construction"'),
    ("dash_tornado_sign", S + "dashboard.py", 'x=[r["at_high"] - r["base"] for r in rows]', 'x=[r["base"] - r["at_high"] for r in rows]'),
    ("readme_bool", S + "readme.py", 'return "yes" if val else "no"', 'return "yes"'),
]


# These three tests read results/mutation.json (or the README that quotes it), which this script writes, so they
# are left out of the mutation runs. Every other test runs against every mutant.
DESELECT = ["tests/test_results.py::test_mutation_report_present",
            "tests/test_readme.py::test_readme_is_rendered_from_results",
            "tests/test_readme.py::test_every_placeholder_resolves_to_a_results_file"]


def run_suite() -> bool:
    cmd = [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"]
    for d in DESELECT:
        cmd += ["--deselect", d]
    r = subprocess.run(cmd, cwd=ROOT,
                       capture_output=True, text=True, timeout=900)
    return r.returncode == 0


def main():
    if not run_suite():
        raise SystemExit("suite fails on unmutated code; fix that first")
    rows = []
    for name, rel, old, new in MUTANTS:
        path = ROOT / rel
        orig = path.read_text(encoding="utf-8")
        if orig.count(old) != 1:
            raise SystemExit(f"{name}: pattern found {orig.count(old)} times in {rel}")
        try:
            path.write_text(orig.replace(old, new), encoding="utf-8", newline="\n")
            survived = run_suite()
        finally:
            path.write_text(orig, encoding="utf-8", newline="\n")
        rows.append({"mutant": name, "file": rel, "killed": not survived})
        print(("KILLED  " if not survived else "SURVIVED"), name, flush=True)
    out = ROOT / "results" / "mutation.json"
    rep = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    run = {"date": dt.date.today().isoformat(), "total": len(rows), "killed": sum(r["killed"] for r in rows),
           "survivors": [r["mutant"] for r in rows if not r["killed"]]}
    rep.setdefault("first_run", run)
    rep.setdefault("history", []).append(run)
    rep["final"] = run
    rep["final_detail"] = rows
    out.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"killed {run['killed']} of {run['total']}")


if __name__ == "__main__":
    main()
