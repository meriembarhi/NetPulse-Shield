"""Tests for the solver entry point using realistic alert-file workflows."""

from pathlib import Path

import pytest

import solver


FIXTURES_DIR = Path(__file__).parent / "fixtures"
ALERTS_FIXTURE = FIXTURES_DIR / "alerts_sample.csv"


class FakeAdvisor:
    def __init__(self, *args, **kwargs):
        pass

    def get_remediation_advice(self, query: str) -> str:
        return f"Mock remediation for: {query}\nApply ACL, lockout, and policy controls."


def test_solver_exits_when_alerts_file_is_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        solver.main()

    assert exc_info.value.code == 1


def test_solver_processes_a_realistic_alert_csv(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(solver, "NetworkSecurityAdvisor", FakeAdvisor)
    Path("alerts.csv").write_text(ALERTS_FIXTURE.read_text(), encoding="utf-8")

    solver.main()

    output = capsys.readouterr().out
    assert "NetPulse-Shield — RAG Advisor (Modular)" in output
    assert "Lateral movement detected" in output
    assert "ACL, lockout, and policy controls" in output