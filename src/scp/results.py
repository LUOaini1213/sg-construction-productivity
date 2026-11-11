"""Compute every result file. Deterministic: same inputs give byte-identical JSON."""
from __future__ import annotations

import json
from pathlib import Path

from . import analysis, data, model

RESULTS = data.ROOT / "results"


def _round(x, nd=6):
    if isinstance(x, float):
        return round(x, nd)
    if isinstance(x, dict):
        return {k: _round(v, nd) for k, v in x.items()}
    if isinstance(x, list):
        return [_round(v, nd) for v in x]
    return x


def model_results() -> dict:
    params = data.model_params()
    base = model.compare(model.values(params))
    figs = {f["id"]: f["value"] for f in data.bca_figures()}
    summary = {k: {m: v for m, v in r.items() if m != "lob"} for k, r in base.items()}
    checks = []
    for c in params["checks_against_cited"]:
        val = summary["ppvc"][c["metric"].replace("ppvc_", "", 1)]
        lo = figs[c["cited_low"]] if "cited_low" in c else None
        hi = figs[c["cited_high"]] if "cited_high" in c else None
        within = (lo is None or val >= lo) and (hi is None or val <= hi)
        checks.append({"metric": c["metric"], "model": val, "cited_low": lo, "cited_high": hi,
                       "within_cited_range": within})
    lob = {k: {"trades": r["lob"]["trades"], "start": r["lob"]["start"], "finish": r["lob"]["finish"]}
           for k, r in base.items() if k in ("conventional", "ppvc")}
    sens = model.sensitivity(params)
    top = {}
    for m in model.HEADLINE:
        rows = sorted((r for r in sens if r["metric"] == m), key=lambda r: -r["swing"])
        top[m] = [r["param"] for r in rows[:3]]
    return {
        "model_base.json": {"scenarios": summary, "checks_against_cited": checks},
        "model_lob.json": lob,
        "model_sensitivity.json": {"rows": sens, "top3_by_swing": top},
        "model_montecarlo.json": model.monte_carlo(params),
    }


def compute_all() -> dict[str, dict]:
    out = {
        "productivity_trend.json": analysis.productivity_trend(),
        "dfma_evidence.json": analysis.dfma_evidence(),
    }
    out.update(model_results())
    return {k: _round(v) for k, v in out.items()}


def dumps(obj) -> str:
    return json.dumps(obj, indent=1, sort_keys=True) + "\n"


def write_all(dest: Path = RESULTS) -> list[Path]:
    dest.mkdir(exist_ok=True)
    paths = []
    for name, obj in compute_all().items():
        p = dest / name
        p.write_text(dumps(obj), encoding="utf-8", newline="\n")
        paths.append(p)
    return paths
