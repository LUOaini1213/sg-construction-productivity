"""Write README.md from templates/README.md.tmpl and results/*.json (offline)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from scp.readme import render  # noqa: E402

(ROOT / "README.md").write_text(render(), encoding="utf-8", newline="\n")
print("wrote README.md")
