import json
import socket
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def guard(*a, **k):
        raise RuntimeError("network access is not allowed in tests")
    monkeypatch.setattr(socket, "socket", guard)
    monkeypatch.setattr(socket, "create_connection", guard)


@pytest.fixture(scope="session")
def recomputed():
    from scp.results import compute_all
    return compute_all()


@pytest.fixture(scope="session")
def committed():
    return {p.name: json.loads(p.read_text(encoding="utf-8")) for p in (ROOT / "results").glob("*.json")}
