"""Render README.md from templates/README.md.tmpl and results/*.json.

Placeholder syntax: {{file.json:dotted.key|format}}  e.g. {{model_base.json:scenarios.ppvc.duration_days|.0f}}
List indices are allowed in the dotted key (adoption_points.0.year). Format defaults to str().
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .data import ROOT

TEMPLATE = ROOT / "templates" / "README.md.tmpl"
PLACEHOLDER = re.compile(r"\{\{([a-z_0-9]+\.json):([A-Za-z0-9_.]+)(?:\|([^}]*))?\}\}")


def lookup(results_dir: Path, fname: str, key: str):
    obj = json.loads((results_dir / fname).read_text(encoding="utf-8"))
    for part in key.split("."):
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    return obj


def render(results_dir: Path = ROOT / "results", template: str | None = None) -> str:
    text = TEMPLATE.read_text(encoding="utf-8") if template is None else template

    def sub(m):
        val = lookup(results_dir, m.group(1), m.group(2))
        fmt = m.group(3)
        if isinstance(val, bool):
            return "yes" if val else "no"
        return format(val, fmt) if fmt else str(val)

    return PLACEHOLDER.sub(sub, text)
