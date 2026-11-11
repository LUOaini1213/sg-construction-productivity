"""Load the committed open-data files (data.gov.sg, Singapore Open Data Licence v1.0)."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"


def _num(s: str):
    s = s.strip().replace(",", "")
    if s in ("", "na", "-"):
        return None
    return float(s)


def singstat_wide(path: Path) -> dict[str, dict[int, float]]:
    """Parse a SingStat wide table: first column is the (indented) series name, then one column per year.

    Returns {series name stripped: {year: value}}. The first occurrence of a name wins, which for these tables
    is the economy-wide or 'Total' block.
    """
    out: dict[str, dict[int, float]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    years = [int(y) for y in rows[0][1:]]
    for row in rows[1:]:
        name = row[0].strip()
        if name in out:
            continue
        series = {}
        for y, v in zip(years, row[1:]):
            x = _num(v)
            if x is not None:
                series[y] = x
        out[name] = series
    return out


def singstat_blocks(path: Path) -> dict[str, dict[str, dict[int, float]]]:
    """Like singstat_wide but keeps every row, grouped under the most recent unindented header row."""
    out: dict[str, dict[str, dict[int, float]]] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    years = [int(y) for y in rows[0][1:]]
    block = None
    for row in rows[1:]:
        raw = row[0]
        name = raw.strip()
        series = {y: _num(v) for y, v in zip(years, row[1:]) if _num(v) is not None}
        if raw == raw.lstrip():
            block = name
            out[block] = {"Total": series}
        else:
            out[block][name] = series
    return out


def construction_va_per_worker() -> dict[int, float]:
    return singstat_wide(RAW / "va_per_worker_chained_annual.csv")["Construction"]


def total_va_per_worker() -> dict[int, float]:
    return singstat_wide(RAW / "va_per_worker_chained_annual.csv")["Total (Based On GDP In Chained (2015) Dollars)"]


def construction_va_per_hour() -> dict[int, float]:
    return singstat_wide(RAW / "va_per_hour_chained_annual.csv")["Construction"]


def total_va_per_hour() -> dict[int, float]:
    return singstat_wide(RAW / "va_per_hour_chained_annual.csv")["Total"]


def contracts_and_payments() -> dict[str, dict[str, dict[int, float]]]:
    return singstat_blocks(RAW / "contracts_progress_annual.csv")


def cmp_work_permits() -> dict[int, float]:
    out = {}
    with open(RAW / "cmp_work_permit.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["work_pass_type"] == "construction_marine_process":
                out[int(r["month"][:4])] = _num(r["count"])
    return out


def bca_figures() -> list[dict]:
    return json.loads((ROOT / "data" / "bca_figures.json").read_text(encoding="utf-8"))["figures"]


def model_params() -> dict:
    return json.loads((ROOT / "params" / "model.json").read_text(encoding="utf-8"))
