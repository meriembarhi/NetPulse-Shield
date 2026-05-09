import json

from db import Alert, AuditLog, get_session

def generate_advice_for_alert(alert_id: int, db_path: str = 'sqlite:///alerts.db'):
    """Task function to generate advice for a single alert.

    This function is intended to be enqueued with RQ. It is safe to call directly
    for testing without Redis.
    """
    try:
        # Import advisor lazily to avoid heavy deps during import-time
        from advisor import NetworkSecurityAdvisor
    except Exception as e:
        raise RuntimeError(f"Advisor unavailable: {e}")

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

    advisor = NetworkSecurityAdvisor()
    advice = advisor.get_remediation_advice(description)

    alert.advice = advice

    # Enregistrement de l'audit local pour tracer la generation des conseils.
    session.add(AuditLog(alert_id=alert.id, action='advice_generated', actor='worker'))
    session.commit()
    session.close()
    return True
