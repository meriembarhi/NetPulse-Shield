"""Tests unitaires pour l'envoi webhook NetPulse-Shield."""

from __future__ import annotations

import json
from types import SimpleNamespace
from urllib import error as urllib_error

import pytest

import webhook


@pytest.fixture
def sample_alert() -> dict:
    """Alerte representative utilisee pour verifier le format du payload JSON."""
    return {
        "alert_id": 42,
        "timestamp": "2026-05-06T12:00:00Z",
        "source_ip": "10.0.0.10",
        "destination_ip": "10.0.0.20",
        "anomaly_score": -0.91,
        "severity": "high",
        "attack_type": "DDoS",
        "description": "Suspicious traffic flood detected",
        "advice": "Enable rate limiting and filter traffic",
    }


def test_load_webhook_config_prefers_argument_then_environment(monkeypatch):
    """Verifie que la configuration explicite prend le dessus sur la variable d'environnement."""
    monkeypatch.setenv("NETPULSE_WEBHOOK_URL", "http://env.example/webhook")

    assert webhook.load_webhook_config("http://explicit.example/webhook") == "http://explicit.example/webhook"
    assert webhook.load_webhook_config() == "http://env.example/webhook"


def test_build_webhook_payload_contains_required_fields(sample_alert):
    """Verifie que le payload contient les champs minimums attendus pour un SIEM."""
    payload = webhook.build_webhook_payload(sample_alert, advice=sample_alert["advice"])

    assert payload["source"] == "NetPulse-Shield"
    assert payload["alert_id"] == 42
    assert payload["source_ip"] == "10.0.0.10"
    assert payload["destination_ip"] == "10.0.0.20"
    assert payload["severity"] == "high"
    assert payload["attack_type"] == "DDoS"
    assert payload["description"]
    assert payload["advice"]


def test_send_alert_via_webhook_succeeds_and_sends_json(monkeypatch, sample_alert):
    """Verifie qu'un webhook configure recoit bien un JSON structure en cas de succes."""
    captured = {}

    class _DummyResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def getcode(self):
            return 200

    def _fake_urlopen(request, timeout=5):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return _DummyResponse()

    monkeypatch.setattr(webhook.urllib_request, "urlopen", _fake_urlopen)

    result = webhook.send_alert_via_webhook(sample_alert, webhook_url="http://siem.local/webhook")

    assert result is True
    assert captured["url"] == "http://siem.local/webhook"
    assert captured["timeout"] == 5
    assert captured["body"]["source"] == "NetPulse-Shield"
    assert captured["body"]["attack_type"] == "DDoS"


def test_send_alert_via_webhook_returns_false_when_unavailable(monkeypatch, sample_alert):
    """Verifie qu'une erreur de connexion est absorbee sans casser l'execution principale."""
    def _raise_url_error(request, timeout=5):
        raise urllib_error.URLError("connection refused")

    monkeypatch.setattr(webhook.urllib_request, "urlopen", _raise_url_error)

    result = webhook.send_alert_via_webhook(sample_alert, webhook_url="http://siem.local/webhook")

    assert result is False


def test_send_alert_via_webhook_is_disabled_when_no_url(monkeypatch, sample_alert):
    """Verifie le comportement optionnel: sans URL, aucun envoi ne doit etre tente."""
    monkeypatch.delenv("NETPULSE_WEBHOOK_URL", raising=False)

    result = webhook.send_alert_via_webhook(sample_alert, webhook_url=None)

    assert result is False
