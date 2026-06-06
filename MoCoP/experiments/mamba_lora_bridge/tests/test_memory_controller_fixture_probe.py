import json
import subprocess
import sys
from pathlib import Path


def test_fixture_probe_outputs_three_modes(tmp_path):
    script = Path(__file__).resolve().parents[1] / "run_memory_controller_fixture_probe.py"
    out = tmp_path / "probe.json"
    result = subprocess.run(
        [sys.executable, str(script), "--output", str(out)],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    assert "runs" in data
    assert {row["mode"] for row in data["runs"]} == {"raw", "modulation", "modulation_plus_evidence"}
    assert any("deep neon purple" in row["prompt"] for row in data["runs"])


def test_fixture_probe_audit_present_for_modulation_modes(tmp_path):
    script = Path(__file__).resolve().parents[1] / "run_memory_controller_fixture_probe.py"
    out = tmp_path / "probe.json"
    subprocess.run(
        [sys.executable, str(script), "--output", str(out)],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    for run in data["runs"]:
        if run["mode"] in ("modulation", "modulation_plus_evidence"):
            assert run["audit"] is not None
            assert "process_count" in run["audit"]
            assert "clean_process_count" in run["audit"]
        elif run["mode"] == "raw":
            assert run["audit"] is None


def test_fixture_probe_no_user_assistant_labels(tmp_path):
    script = Path(__file__).resolve().parents[1] / "run_memory_controller_fixture_probe.py"
    out = tmp_path / "probe.json"
    subprocess.run(
        [sys.executable, str(script), "--output", str(out)],
        check=True,
        text=True,
        capture_output=True,
    )
    data = json.loads(out.read_text(encoding="utf-8"))
    for run in data["runs"]:
        if run["mode"] in ("modulation", "modulation_plus_evidence"):
            prompt_lower = run["prompt"].lower()
            # Check that modulation block portion does not contain user:/assistant: labels.
            # The raw recall block (in modulation_plus_evidence) may use "You said:" etc.
            # but the modulation packet section itself must not.
            if "[Private memory orientation]" in run["prompt"]:
                orientation_start = run["prompt"].index("[Private memory orientation]")
                orientation_end = run["prompt"].index("[/Private memory orientation]") + len("[/Private memory orientation]")
                orientation_block = run["prompt"][orientation_start:orientation_end].lower()
                assert "user:" not in orientation_block
                assert "assistant:" not in orientation_block
