"""Utilitaires webhook pour envoyer les alertes NetPulse-Shield vers un SIEM.

Le module reste volontairement léger et sans dépendance externe lourde.
Il utilise uniquement la standard library pour éviter de casser le projet
si le webhook n'est pas configuré ou si le SIEM est temporairement indisponible.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timezone
from typing import Any, Mapping
from urllib import error as urllib_error
from urllib import request as urllib_request


logger = logging.getLogger(__name__)


def load_webhook_config(explicit_url: str | None = None) -> str | None:
    """Charge l'URL webhook depuis l'argument ou la variable d'environnement.

    Priorite:
    1. argument explicite
    2. variable d'environnement NETPULSE_WEBHOOK_URL
    3. aucune configuration disponible
    """

    if explicit_url and explicit_url.strip():
        return explicit_url.strip()

    env_url = os.getenv("NETPULSE_WEBHOOK_URL", "").strip()
    return env_url or None


def load_webhook_profile(explicit_profile: str | None = None) -> str:
    """Charge le profil d'envoi webhook.

    Valeurs supportees: generic, wazuh.
    """

    if explicit_profile and explicit_profile.strip():
        return explicit_profile.strip().lower()

    env_profile = os.getenv("NETPULSE_WEBHOOK_PROFILE", "generic").strip().lower()
    return env_profile or "generic"


def _json_safe(value: Any) -> Any:
    """Convertit les objets non serialisables en valeurs JSON sures."""

    if value is None:
        return None

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    # Pandas / NumPy renvoient souvent des scalaires qui ne sont pas JSON natifs.
    if hasattr(value, "item") and not isinstance(value, (str, bytes, bytearray)):
        try:
            return value.item()
        except Exception:
            pass

    return value


def _is_missing(value: Any) -> bool:
    """Indique si une valeur doit etre consideree comme absente."""

    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return value != value
    except Exception:
        return False


def _first_non_empty(payload: Mapping[str, Any], keys: list[str]) -> Any:
    """Retourne la premiere valeur non vide trouvee parmi plusieurs aliases."""

    for key in keys:
        value = payload.get(key)
        if not _is_missing(value):
            return value
    return None


def build_webhook_payload(
    alert: Mapping[str, Any],
    advice: str | None = None,
    profile: str = "generic",
) -> dict[str, Any]:
    """Construit un payload JSON standardise pour les SIEM ou webhooks externes."""

    severity = _first_non_empty(alert, ["severity", "risk_level"])
    anomaly_score = alert.get("anomaly_score")

    if severity is None:
        try:
            score = float(anomaly_score) if anomaly_score is not None else 0.0
        except Exception:
            score = 0.0

        if score <= -0.8:
            severity = "high"
        elif score <= -0.4:
            severity = "medium"
        else:
            severity = "low"

    timestamp = _first_non_empty(alert, ["timestamp", "created_at", "detected_at"])
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    description = _first_non_empty(alert, ["description", "summary", "message"])
    if description is None:
        description = (
            f"Anomalie reseau detectee avec score {anomaly_score}"
            if anomaly_score is not None
            else "Anomalie reseau detectee"
        )

    source_ip = _first_non_empty(
        alert,
        ["source_ip", "src_ip", "srcip", "srcaddr", "saddr", "source", "SrcAddr"],
    )
    destination_ip = _first_non_empty(
        alert,
        ["destination_ip", "dst_ip", "dstip", "dstaddr", "daddr", "destination", "DstAddr"],
    )

    attack_type = _first_non_empty(alert, ["attack_type", "label", "threat_type", "signature"])

    alert_id = _first_non_empty(alert, ["alert_id", "id", "event_id", "uuid"])
    if alert_id is None:
        alert_id = f"alert-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

    payload = {
        "source": "NetPulse-Shield",
        "timestamp": _json_safe(timestamp),
        "alert_id": _json_safe(alert_id),
        "source_ip": _json_safe(source_ip),
        "destination_ip": _json_safe(destination_ip),
        "anomaly_score": _json_safe(anomaly_score),
        "severity": str(severity).lower() if severity is not None else "medium",
        "attack_type": _json_safe(attack_type),
        "description": _json_safe(description),
        "advice": _json_safe(advice if advice is not None else alert.get("advice")),
    }

    if profile == "wazuh":
        payload = {
            **payload,
            "integration": "NetPulse-Shield",
            "event_type": "network_anomaly",
            "location": "NetPulse-Shield",
            "rule": {
                "id": "100001",
                "level": 10 if payload["severity"] == "high" else 7 if payload["severity"] == "medium" else 3,
                "description": "NetPulse-Shield anomaly alert",
                "groups": ["netpulse", "network", "anomaly"],
            },
            "agent": {
                "name": "NetPulse-Shield",
                "id": "000",
            },
            "manager": {
                "name": "wazuh",
            },
            "data": {
                "source_ip": payload.get("source_ip"),
                "destination_ip": payload.get("destination_ip"),
                "anomaly_score": payload.get("anomaly_score"),
                "severity": payload.get("severity"),
                "attack_type": payload.get("attack_type"),
                "description": payload.get("description"),
                "advice": payload.get("advice"),
            },
            "full_log": f"NetPulse-Shield anomaly alert: {payload.get('description')}",
        }

    return payload


def send_alert_via_webhook(
    alert: Mapping[str, Any],
    webhook_url: str | None = None,
    timeout: int = 5,
    advice: str | None = None,
    profile: str | None = None,
) -> bool:
    """Envoie une alerte via webhook en JSON.

    Cette fonction ne doit jamais casser le pipeline principal:
    - si le webhook n'est pas configure, elle retourne False
    - si l'appel echoue, elle journalise l'erreur et retourne False
    - en cas de succes, elle retourne True
    """

    target_url = load_webhook_config(webhook_url)
    if not target_url:
        logger.info("Webhook non configure: envoi ignore.")
        return False

    target_profile = load_webhook_profile(profile)
    payload = build_webhook_payload(alert, advice=advice, profile=target_profile)
    body = json.dumps(payload, ensure_ascii=False, default=_json_safe).encode("utf-8")

    request = urllib_request.Request(
        target_url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "NetPulse-Shield/1.0"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(request, timeout=timeout) as response:
            status_code = getattr(response, "status", response.getcode())
            if 200 <= int(status_code) < 300:
                logger.info("Webhook (%s) envoye avec succes vers %s", target_profile, target_url)
                return True

            logger.warning("Webhook (%s) repondu avec le statut HTTP %s vers %s", target_profile, status_code, target_url)
            return False
    except urllib_error.HTTPError as exc:
        logger.warning("Webhook (%s) refuse avec HTTP %s vers %s: %s", target_profile, exc.code, target_url, exc)
    except urllib_error.URLError as exc:
        logger.warning("Webhook (%s) indisponible vers %s: %s", target_profile, target_url, exc)
    except TimeoutError as exc:
        logger.warning("Webhook (%s) en timeout vers %s: %s", target_profile, target_url, exc)
    except Exception as exc:
        logger.exception("Erreur inattendue lors de l'envoi du webhook (%s) vers %s: %s", target_profile, target_url, exc)

    return False
