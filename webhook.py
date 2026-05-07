#!/usr/bin/env python
"""Webhook sender for NetPulse-Shield alerts.

This module sends alert payloads to a generic webhook URL for quick testing
and to Azure Log Analytics / Microsoft Sentinel when Azure credentials are
available.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _build_azure_signature(workspace_id: str, primary_key: str, body: bytes, rfc1123_date: str) -> str:
    string_to_hash = f"POST\n{len(body)}\napplication/json\nx-ms-date:{rfc1123_date}\n/api/logs"
    decoded_key = base64.b64decode(primary_key)
    digest = hmac.new(decoded_key, string_to_hash.encode("utf-8"), hashlib.sha256).digest()
    signature = base64.b64encode(digest).decode("utf-8")
    return f"SharedKey {workspace_id}:{signature}"


def _build_payload(alert: dict, advice: str | None = None) -> dict:
    payload = {
        "source": "NetPulse-Shield",
        "timestamp": alert.get("timestamp"),
        "alert_id": alert.get("alert_id"),
        "severity": alert.get("severity", "medium"),
        "anomaly_score": alert.get("anomaly_score"),
        "source_ip": alert.get("source_ip"),
        "destination_ip": alert.get("destination_ip"),
        "attack_type": alert.get("attack_type"),
        "description": alert.get("description"),
        "advice": advice,
    }
    return {key: value for key, value in payload.items() if value is not None}


def send_alert_to_azure(
    alert: dict,
    webhook_url: str | None = None,
    advice: str | None = None,
    workspace_id: str | None = None,
    primary_key: str | None = None,
    log_type: str = "NetPulseAlerts",
    timeout: int = 5,
) -> bool:
    """Send one alert to a generic webhook or to Azure Log Analytics.

    If workspace_id and primary_key are provided, the function uses Azure's
    Data Collector API. Otherwise it sends a normal JSON POST to webhook_url,
    which is useful for webhook.site testing.
    """

    webhook_url = webhook_url or os.getenv("NETPULSE_WEBHOOK_URL")
    workspace_id = workspace_id or os.getenv("NETPULSE_WORKSPACE_ID")
    primary_key = primary_key or os.getenv("NETPULSE_PRIMARY_KEY")

    if not webhook_url:
        logger.warning("Webhook URL is not configured")
        return False

    payload = _build_payload(alert, advice=advice)

    try:
        if workspace_id and primary_key:
            body = json.dumps([payload]).encode("utf-8")
            rfc1123_date = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
            signature = _build_azure_signature(workspace_id, primary_key, body, rfc1123_date)

            request = urllib.request.Request(
                webhook_url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": signature,
                    "Log-Type": log_type,
                    "x-ms-date": rfc1123_date,
                },
                method="POST",
            )
        else:
            body = json.dumps(payload).encode("utf-8")
            request = urllib.request.Request(
                webhook_url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            if 200 <= response.status < 300:
                logger.info("Sent alert to webhook endpoint")
                return True

            logger.warning("Webhook returned status %s", response.status)
            return False

    except urllib.error.HTTPError as exc:
        logger.warning("Webhook request failed with HTTP error: %s", exc)
    except urllib.error.URLError as exc:
        logger.warning("Webhook request failed with URL error: %s", exc)
    except Exception as exc:
        logger.warning("Webhook request failed: %s", exc)

    return False