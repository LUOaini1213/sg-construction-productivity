"""Write dashboard/index.html from results/*.json (offline)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scp.dashboard import render  # noqa: E402

res = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "results").glob("*.json")}
(ROOT / "dashboard").mkdir(exist_ok=True)
(ROOT / "dashboard" / "index.html").write_text(render(res), encoding="utf-8", newline="\n")
print("wrote dashboard/index.html")
