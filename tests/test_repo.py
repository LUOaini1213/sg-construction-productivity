import json
import re
import subprocess

import yaml

from conftest import ROOT

TEXT_SUFFIXES = {".py", ".md", ".json", ".csv", ".yml", ".tmpl", ".html", ".txt", ".ini", ".cfg", ""}


def _tracked_files():
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        files = [ROOT / f for f in out.splitlines()]
    except (OSError, subprocess.CalledProcessError):
        files = []
    if not files:
        files = [p for p in ROOT.rglob("*")
                 if p.is_file() and not {".venv", ".git", "__pycache__"} & set(p.parts)]
    return [p for p in files if p.suffix in TEXT_SUFFIXES and p.is_file()]


def test_ci_yaml_parses_and_runs_pytest_offline():
    wf = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8"))
    steps = wf["jobs"]["test"]["steps"]
    runs = " ".join(s.get("run", "") for s in steps)
    assert "pytest" in runs and "fetch_data" not in runs


def test_mit_licence():
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")


def test_no_absolute_local_paths_or_private_terms():
    pat = re.compile(r"[A-Za-z]:\\+Users|[A-Za-z]:/Users|/Users/|/home/|AppData|internship|\bintern\b", re.I)
    files = _tracked_files()
    assert len(files) > 20
    for p in files:
        if p.name == "test_repo.py":
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        assert not pat.search(text), p.relative_to(ROOT)


def test_sources_doc_covers_every_dataset_and_figure():
    src = (ROOT / "docs/sources.md").read_text(encoding="utf-8")
    m = json.loads((ROOT / "data/raw/manifest.json").read_text(encoding="utf-8"))
    for d in m["datasets"].values():
        assert d["datasetId"] in src
    assert m["retrieved"] in src
    for f in json.loads((ROOT / "data/bca_figures.json").read_text(encoding="utf-8"))["figures"]:
        assert f["url"] in src, f["id"]
    assert "could not verify" in src.lower()


def test_requirements_are_pinned():
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            assert re.fullmatch(r"[A-Za-z0-9_.\-]+==[0-9][A-Za-z0-9.]*", line.strip()), line
