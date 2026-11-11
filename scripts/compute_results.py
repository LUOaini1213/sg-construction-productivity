"""Recompute results/*.json from data/ and params/ (offline)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scp.results import write_all  # noqa: E402

for p in write_all():
    print("wrote", p.relative_to(Path(__file__).resolve().parents[1]).as_posix())
