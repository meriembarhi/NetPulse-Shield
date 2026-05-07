from __future__ import annotations

import json

import webhook


class _FakeResponse:
    def __init__(self, status: int = 202):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_send_alert_to_azure_uses_azure_data_collector_payload(monkeypatch):
    captured_request = {}

    def fake_signature(workspace_id, primary_key, body, rfc1123_date):
        captured_request["signature_args"] = (workspace_id, primary_key, body, rfc1123_date)
        return "SharedKey workspace:test-signature"

    def fake_request(url, data=None, headers=None, method=None):
        captured_request["request"] = {
            "url": url,
            "data": data,
            "headers": headers,
            "method": method,
        }
        return object()

    def fake_urlopen(request, timeout=0):
        captured_request["urlopen_timeout"] = timeout
        captured_request["urlopen_request"] = request
        return _FakeResponse(status=202)

    monkeypatch.setenv("NETPULSE_WEBHOOK_URL", "https://example.azure.com/api/logs")
    monkeypatch.setenv("NETPULSE_WORKSPACE_ID", "workspace")
    monkeypatch.setenv("NETPULSE_PRIMARY_KEY", "cHJpbWFyeS1rZXk=")
    monkeypatch.setattr(webhook, "_build_azure_signature", fake_signature)
    monkeypatch.setattr(webhook.urllib.request, "Request", fake_request)
    monkeypatch.setattr(webhook.urllib.request, "urlopen", fake_urlopen)

    alert = {
        "timestamp": "2026-05-07T10:30:00Z",
        "alert_id": 123,
        "severity": "high",
        "anomaly_score": -0.95,
        "source_ip": "10.0.0.5",
        "destination_ip": "10.0.0.20",
        "attack_type": "DDoS",
        "description": "Suspicious traffic pattern",
    }

    result = webhook.send_alert_to_azure(alert, advice="Block source IP")

    assert result is True
    assert captured_request["request"]["url"] == "https://example.azure.com/api/logs"
    assert captured_request["request"]["method"] == "POST"
    assert captured_request["request"]["headers"]["Content-Type"] == "application/json"
    assert captured_request["request"]["headers"]["Authorization"] == "SharedKey workspace:test-signature"
    assert captured_request["request"]["headers"]["Log-Type"] == "NetPulseAlerts"
    assert captured_request["request"]["headers"]["x-ms-date"] == captured_request["signature_args"][3]
    assert captured_request["urlopen_timeout"] == 5

    sent_payload = json.loads(captured_request["request"]["data"].decode("utf-8"))
    assert isinstance(sent_payload, list)
    assert sent_payload == [
        {
            "source": "NetPulse-Shield",
            "timestamp": "2026-05-07T10:30:00Z",
            "alert_id": 123,
            "severity": "high",
            "anomaly_score": -0.95,
            "source_ip": "10.0.0.5",
            "destination_ip": "10.0.0.20",
            "attack_type": "DDoS",
            "description": "Suspicious traffic pattern",
            "advice": "Block source IP",
        }
    ]
