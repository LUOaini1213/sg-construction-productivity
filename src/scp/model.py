"""Illustrative manpower / duration / site-productivity model with a line-of-balance (LOB) schedule.

Everything here is a function of params/model.json. Nothing is calibrated to a real project.
"""
from __future__ import annotations

import math
import random

SCENARIOS = ("conventional", "precast", "precast_prefab_mep", "ppvc")


def values(params: dict) -> dict[str, float]:
    return {k: v["value"] for k, v in params["params"].items()}


def line_of_balance(trades: list[tuple[str, float]], floors: int, buffer: float,
                    first_trade_ready: list[float] | None = None) -> dict:
    """One crew per trade, working floor by floor upwards.

    start[i][f] = max(finish[i][f-1], finish[i-1][f] + buffer, ready[f] for the first trade).
    Returns start/finish matrices and the finish of the last trade on the top floor.
    """
    n = len(trades)
    start = [[0.0] * floors for _ in range(n)]
    finish = [[0.0] * floors for _ in range(n)]
    for i, (_, d) in enumerate(trades):
        for f in range(floors):
            s = 0.0
            if f > 0:
                s = max(s, finish[i][f - 1])
            if i > 0:
                s = max(s, finish[i - 1][f] + buffer)
            elif first_trade_ready is not None:
                s = max(s, first_trade_ready[f])
            start[i][f] = s
            finish[i][f] = s + d
    return {"trades": [t for t, _ in trades], "start": start, "finish": finish,
            "end": finish[-1][-1]}


def _labour_shares(p: dict) -> dict[str, float]:
    arch = 1.0 - p["share_substructure"] - p["share_structure"] - p["share_mep"]
    if arch <= 0:
        raise ValueError("labour shares exceed 1")
    return {"substructure": p["share_substructure"], "structure": p["share_structure"],
            "mep": p["share_mep"], "arch": arch}


def scenario(p: dict, name: str) -> dict:
    floors = int(round(p["floors"]))
    gfa = floors * p["gfa_per_floor"]
    base_md = p["conv_md_per_m2"] * gfa
    sh = _labour_shares(p)
    cut = {"substructure": 0.0, "structure": 0.0, "mep": 0.0, "arch": 0.0}
    extra_md = 0.0
    ready = None
    s, m, a = p["conv_structure_days"], p["conv_mep_days"], p["conv_arch_days"]
    if name == "conventional":
        trades = [("structure", s), ("mep", m), ("arch", a)]
    elif name == "precast":
        cut["structure"] = p["precast_structure_labour_cut"]
        trades = [("structure", s * (1 - p["precast_cycle_cut"])), ("mep", m), ("arch", a)]
    elif name == "precast_prefab_mep":
        cut["structure"] = p["precast_structure_labour_cut"]
        cut["mep"] = p["prefab_mep_labour_cut"]
        trades = [("structure", s * (1 - p["precast_cycle_cut"])),
                  ("mep", m * (1 - p["prefab_mep_time_cut"])), ("arch", a)]
    elif name == "ppvc":
        cut["structure"] = p["ppvc_structure_labour_cut"]
        cut["mep"] = p["ppvc_mep_labour_cut"]
        cut["arch"] = p["ppvc_arch_labour_cut"]
        mods = p["modules_per_floor"]
        extra_md = p["install_md_per_module"] * mods * floors
        install = mods / p["crane_modules_per_day"]
        rate = p["factory_modules_per_day"]
        ready = [-p["factory_lead_days"] + (f + 1) * mods / rate for f in range(floors)]
        trades = [("module install", install), ("connections", p["ppvc_connect_days"]),
                  ("finishing", p["ppvc_finish_days"])]
    else:
        raise KeyError(name)
    lob = line_of_balance(trades, floors, p["trade_buffer_days"], ready)
    site_md = sum(base_md * sh[k] * (1 - cut[k]) for k in sh) + extra_md
    duration = p["substructure_days"] + lob["end"] + p["tail_days"]
    return {
        "scenario": name,
        "gfa_m2": gfa,
        "site_man_days": site_md,
        "duration_days": duration,
        "superstructure_days": lob["end"],
        "time_per_floor_days": lob["end"] / floors,
        "takt_days": max(d for _, d in trades),
        "bottleneck_trade": max(trades, key=lambda t: t[1])[0],
        "factory_days_per_floor": (p["modules_per_floor"] / p["factory_modules_per_day"]) if name == "ppvc" else None,
        "avg_site_headcount": site_md / duration,
        "site_productivity_m2_per_md": gfa / site_md,
        "lob": lob,
    }


def compare(p: dict) -> dict:
    res = {n: scenario(p, n) for n in SCENARIOS}
    c = res["conventional"]
    for r in res.values():
        r["manpower_saving_pct"] = 100 * (1 - r["site_man_days"] / c["site_man_days"])
        r["duration_saving_days"] = c["duration_days"] - r["duration_days"]
        r["duration_saving_months"] = r["duration_saving_days"] / (365.25 / 12)
        r["time_per_floor_cut_pct"] = 100 * (1 - r["time_per_floor_days"] / c["time_per_floor_days"])
        r["productivity_ratio"] = r["site_productivity_m2_per_md"] / c["site_productivity_m2_per_md"]
    return res


HEADLINE = ("manpower_saving_pct", "duration_saving_days", "productivity_ratio")


def sensitivity(params: dict, scen: str = "ppvc") -> list[dict]:
    """One-at-a-time sweep: each assumption set to its low and high bound, others at base value."""
    base = values(params)
    b = compare(base)[scen]
    rows = []
    for k, spec in params["params"].items():
        lo, hi = dict(base), dict(base)
        lo[k], hi[k] = spec["low"], spec["high"]
        rl, rh = compare(lo)[scen], compare(hi)[scen]
        for metric in HEADLINE:
            rows.append({"param": k, "metric": metric, "base": b[metric],
                         "at_low": rl[metric], "at_high": rh[metric],
                         "swing": abs(rh[metric] - rl[metric])})
    return rows


def monte_carlo(params: dict, scen: str = "ppvc") -> dict:
    mc = params["monte_carlo"]
    rng = random.Random(mc["seed"])
    draws = {m: [] for m in HEADLINE + ("time_per_floor_cut_pct", "duration_saving_months")}
    for _ in range(mc["samples"]):
        p = {k: rng.triangular(s["low"], s["high"], s["value"]) for k, s in params["params"].items()}
        r = compare(p)[scen]
        for m in draws:
            draws[m].append(r[m])
    out = {}
    for m, xs in draws.items():
        xs.sort()
        out[m] = {q: _quantile(xs, q / 100) for q in (5, 50, 95)}
        out[m] = {f"p{q}": v for q, v in out[m].items()}
    out["samples"] = mc["samples"]
    return out


def _quantile(xs: list[float], q: float) -> float:
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)
