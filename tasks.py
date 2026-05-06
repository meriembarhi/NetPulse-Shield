import json

from db import Alert, AuditLog, get_session
from webhook import send_alert_via_webhook

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

    # On envoie aussi l'alerte vers le SIEM si un webhook a ete configure.
    # Cette etape reste optionnelle et ne doit jamais bloquer le worker.
    webhook_payload = {
        "alert_id": alert.id,
        "anomaly_score": alert.anomaly_score,
        "severity": getattr(alert, "severity", None),
        "description": description,
        "advice": advice,
    }
    try:
        features = json.loads(alert.feature_json or "{}")
        webhook_payload.update(features)
    except Exception:
        pass

    send_alert_via_webhook(webhook_payload, advice=advice)

    # Enregistrement de l'audit local pour tracer la generation des conseils.
    session.add(AuditLog(alert_id=alert.id, action='advice_generated', actor='worker'))
    session.commit()
    session.close()
    return True
