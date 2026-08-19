import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_governance_baseline_passes():
    result = subprocess.run(
        [sys.executable, "scripts/govern.py", "--ci"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    report = json.loads((ROOT / "reports/latest/change-report.json").read_text(encoding="utf-8"))
    assert report["status"] == "PASS"
    assert report["changeLevel"] == "NONE"
    assert report["suggestedVersion"] == report["baselineVersion"]
