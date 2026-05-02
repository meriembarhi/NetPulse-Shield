"""End-to-end integration test for detector -> alerts.csv -> solver."""

from pathlib import Path

import pandas as pd

import solver
from detector import NetworkAnomalyDetector


FIXTURES_DIR = Path(__file__).parent / "fixtures"
DETECTOR_FIXTURE = FIXTURES_DIR / "detector_sample.csv"


class FakeAdvisor:
    def __init__(self, *args, **kwargs):
        pass

    def get_remediation_advice(self, query: str) -> str:
        return f"Integration test remediation for: {query}\nApply ACL and lockout controls."


def test_detector_to_solver_pipeline(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(solver, "NetworkSecurityAdvisor", FakeAdvisor)

    input_df = pd.read_csv(DETECTOR_FIXTURE)
    detector = NetworkAnomalyDetector(
        contamination=0.1,
        model_path=str(tmp_path / "models" / "netpulse_model.joblib"),
    )

    detected = detector.analyze(input_df, force_train=True)
    alerts = detected[detected["is_anomaly"]].sort_values(by="anomaly_score").head(5)
    alerts.to_csv("alerts.csv", index=False)

    assert Path("alerts.csv").exists()
    assert len(alerts) > 0

    solver.main()

    output = capsys.readouterr().out
    assert "NetPulse-Shield — RAG Advisor (Modular)" in output
    assert "Alerts detected. Initializing RAG Remediation Pipeline" in output
    assert "Lateral movement detected via internal port scanning on port 445." in output
    assert "Integration test remediation for:" in output