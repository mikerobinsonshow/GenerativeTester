import asyncio
import sys
from pathlib import Path


def test_demo_run(monkeypatch):
    project_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(project_root)
    sys.path.insert(0, str(project_root))
    from runner import run

    log = asyncio.run(run("config/target.json"))
    assert isinstance(log, dict)
    assert Path("artifacts/before.png").exists()
    assert Path("artifacts/after.png").exists()
    assert Path("artifacts/log.json").exists()
