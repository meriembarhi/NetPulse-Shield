import json
import os

from db import Alert, AuditLog, get_session


def generate_advice_for_alert(
    alert_id: int,
    db_path: str = "sqlite:///alerts.db",
    remediation_backend: str | None = None,
):
    """Task function to generate advice for a single alert.

    remediation_backend
        ``\"rag\"`` or ``\"ollama\"``. If ``None``, uses ``NETPULSE_REMEDIATION_MODE``
        (default ``rag``) so RQ workers pick up the env set before ``rq worker``.
    """
    mode = (remediation_backend or os.getenv("NETPULSE_REMEDIATION_MODE", "rag")).strip().lower()

    try:
        if mode == "ollama":
            from remediator import get_remediation_advice as get_advice
        else:
            from advisor import NetworkSecurityAdvisor

            _advisor = NetworkSecurityAdvisor()
            get_advice = _advisor.get_remediation_advice
    except Exception as e:
        raise RuntimeError(f"Remediation backend unavailable ({mode}): {e}") from e

    session = get_session(db_path)
    alert = session.query(Alert).filter(Alert.id == int(alert_id)).one_or_none()
    if alert is None:
        session.close()
        raise ValueError(f"Alert id={alert_id} not found")

    # Build description
    try:
        features = json.loads(alert.feature_json or "{}")
        description = f"Anomalous flow - score={alert.anomaly_score} features={list(features.keys())}"
    except Exception:
        description = f"Anomalous flow - score={alert.anomaly_score}"

    advice = get_advice(description)

    alert.advice = advice

    # Enregistrement de l'audit local pour tracer la generation des conseils.
    session.add(AuditLog(alert_id=alert.id, action='advice_generated', actor='worker'))
    session.commit()
    session.close()
    return True
