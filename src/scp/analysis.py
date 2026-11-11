"""Productivity trend and what the open data can say about DfMA."""
from __future__ import annotations

import math
import random

from . import data

HOURS_PER_MAN_DAY = 8  # conversion assumption, used only to restate VA per hour as VA per man-day equivalent
# Two-tailed 5% critical value of Pearson r with n - 2 = 2 degrees of freedom (standard table value).
R_CRIT_DF2 = 0.950


def cagr(series: dict[int, float], y0: int, y1: int) -> float:
    return 100 * ((series[y1] / series[y0]) ** (1 / (y1 - y0)) - 1)


def loglinear_trend(series: dict[int, float], y0: int, y1: int, exclude=(), n_boot=2000, seed=20261111) -> dict:
    """OLS of ln(value) on year; growth % per year with a residual-bootstrap 95% interval."""
    pts = [(y, math.log(series[y])) for y in range(y0, y1 + 1) if y in series and y not in exclude]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    def fit(xv, yv):
        mx, my = sum(xv) / len(xv), sum(yv) / len(yv)
        sxx = sum((x - mx) ** 2 for x in xv)
        b = sum((x - mx) * (y - my) for x, y in zip(xv, yv)) / sxx
        return b, my - b * mx

    b, a = fit(xs, ys)
    resid = [y - (a + b * x) for x, y in zip(xs, ys)]
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        yb = [a + b * x + rng.choice(resid) for x in xs]
        boots.append(fit(xs, yb)[0])
    boots.sort()
    lo, hi = boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot) - 1]
    g = lambda s: 100 * (math.exp(s) - 1)  # noqa: E731
    return {"years": f"{y0}-{y1}", "excluded": list(exclude), "n_points": len(xs),
            "growth_pct_per_year": g(b), "ci95_low": g(lo), "ci95_high": g(hi)}


def productivity_trend() -> dict:
    w, h = data.construction_va_per_worker(), data.construction_va_per_hour()
    tw, th = data.total_va_per_worker(), data.total_va_per_hour()
    last = max(h)
    first_h = min(h)
    out = {
        "definitions": {
            "va_per_worker": "Gross value added of the construction industry in chained (2015) S$ divided by "
                             "employment (SingStat & MOM, table M015761, SSIC 2020)",
            "va_per_hour": "Gross value added in chained (2015) S$ per actual hour worked (SingStat & MOM, "
                           "table M015851, SSIC 2020)",
            "va_per_man_day_equiv": f"VA per actual hour x {HOURS_PER_MAN_DAY} hours; a unit conversion, not a "
                                    "published series",
        },
        "latest_year": last,
        "hours_per_man_day": HOURS_PER_MAN_DAY,
        "first_year_hourly": first_h,
        "va_per_worker_latest": w[last],
        "va_per_worker_2019": w[2019],
        "va_per_worker_2020": w[2020],
        "covid_2020_drop_pct": 100 * (w[2020] / w[2019] - 1),
        "va_per_hour_latest": h[last],
        "va_per_hour_first": h[first_h],
        "va_per_hour_2019": h[2019],
        "va_per_man_day_equiv_latest": h[last] * HOURS_PER_MAN_DAY,
        "construction_vs_total_per_hour_pct_first": 100 * h[first_h] / th[first_h],
        "construction_vs_total_per_hour_pct_latest": 100 * h[last] / th[last],
        "implied_hours_per_worker_latest": w[last] / h[last],
        "cagr_va_per_hour_full_pct": cagr(h, first_h, last),
        "cagr_va_per_hour_total_economy_pct": cagr(th, first_h, last),
        "cagr_va_per_hour_2009_2019_pct": cagr(h, 2009, 2019),
        "cagr_va_per_hour_2019_latest_pct": cagr(h, 2019, last),
        "cagr_va_per_worker_2009_2019_pct": cagr(w, 2009, 2019),
        "trend_va_per_hour_excl_covid": loglinear_trend(h, first_h, last, exclude=(2020, 2021)),
        "trend_va_per_hour_all": loglinear_trend(h, first_h, last),
        "series": {
            "year": sorted(h),
            "va_per_hour": [h[y] for y in sorted(h)],
            "va_per_hour_total": [th[y] for y in sorted(h)],
            "va_per_worker": [w[y] for y in sorted(h)],
        },
    }
    return out


def dfma_evidence() -> dict:
    figs = {f["id"]: f for f in data.bca_figures()}
    adoption = sorted((f["ref_year"], f["value"]) for f in figs.values() if f["kind"] == "adoption")
    h = data.construction_va_per_hour()
    pairs = [(y, a, h[y]) for y, a in adoption if y in h]
    xs, ys = [p[1] for p in pairs], [p[2] for p in pairs]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    r = (sum((x - mx) * (y - my) for x, y in zip(xs, ys))
         / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)))
    y0, y1 = pairs[0][0], pairs[-1][0]
    cp = data.contracts_and_payments()
    ca = cp["Contracts Awarded - Total Public & Private Sector"]
    pp = cp["Progress Payments Certified - Total Public & Private Sector"]
    last = max(ca["Total"])
    wp = data.cmp_work_permits()
    return {
        "adoption_points": [{"year": y, "adoption_pct": a, "va_per_hour": v} for y, a, v in pairs],
        "n_points": len(pairs),
        "adoption_change_pts": pairs[-1][1] - pairs[0][1],
        "adoption_first_year": y0, "adoption_last_year": y1,
        "va_per_hour_change_pct_same_years": 100 * (pairs[-1][2] / pairs[0][2] - 1),
        "pearson_r": r,
        "r_critical_5pct_df2": R_CRIT_DF2,
        "demand_latest_year": last,
        "contracts_awarded_latest_sgd_m": ca["Total"][last],
        "progress_payments_latest_sgd_m": pp["Total"][last],
        "building_share_of_contracts_latest_pct": 100 * ca["Building Work"][last] / ca["Total"][last],
        "building_share_of_payments_latest_pct": 100 * pp["Building Work"][last] / pp["Total"][last],
        "contracts_awarded_growth_2019_latest_pct": 100 * (ca["Total"][last] / ca["Total"][2019] - 1),
        "cmp_work_permits": {str(y): v for y, v in sorted(wp.items())},
        "cmp_2019_to_2020_pct": 100 * (wp[2020] / wp[2019] - 1),
        "cmp_latest_year": max(wp),
        "cmp_latest": wp[max(wp)],
        "series": {
            "year": sorted(ca["Total"]),
            "contracts_awarded": [ca["Total"][y] for y in sorted(ca["Total"])],
            "progress_payments": [pp["Total"][y] for y in sorted(ca["Total"])],
        },
    }
