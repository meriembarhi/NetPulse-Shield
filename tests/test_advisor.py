"""Tests unitaires et d'integration pour la couche RAG / Advisor."""

from __future__ import annotations

import builtins
import time

import pytest
from langchain_core.documents import Document

import advisor
import embeddings
from advisor import NetworkSecurityAdvisor
from knowledge_base import load_knowledge_base


class _KeywordAwareRetriever:
    """Retriever factice qui renvoie des conseils selon les mots du query."""

    def invoke(self, query: str):
        q = (query or "").lower()
        if "ddos" in q or "sload" in q or "flood" in q:
            return [
                Document(
                    page_content=(
                        "DDoS remediation: enable rate-limiting, apply ACL filtering, "
                        "and activate scrubbing."
                    )
                )
            ]
        if "scan" in q or "port 445" in q or "lateral" in q:
            return [
                Document(
                    page_content=(
                        "Scanning/lateral movement remediation: isolate host, "
                        "segment network, and audit SMB logs."
                    )
                )
            ]
        return [
            Document(
                page_content=(
                    "Generic remediation: collect evidence, review firewall rules, "
                    "and monitor suspicious traffic."
                )
            )
        ]


@pytest.fixture
def anomaly_description() -> str:
    """Description d'anomalie representative pour les tests de base."""
    return "Lateral movement detected via internal port scanning on port 445."


@pytest.fixture
def realistic_alert() -> dict:
    """Alerte reseau realiste inspirée des champs utilises par le projet."""
    return {
        "anomaly_score": -0.72,
        "sttl": 254,
        "Sload": 1_500_000_000,
        "sbytes": 5400,
        "dbytes": 240,
        "service": "-",
        "proto": "tcp",
    }


@pytest.fixture
def fast_advisor(monkeypatch) -> NetworkSecurityAdvisor:
    """Advisor initialise sans dependances externes lourdes pour des tests rapides."""

    def _fake_initialize(self):
        self.vector_store = object()
        self.retriever = _KeywordAwareRetriever()

    monkeypatch.setattr(NetworkSecurityAdvisor, "_initialize_vector_store", _fake_initialize)
    return NetworkSecurityAdvisor(top_k=3)


def _alert_to_description(alert: dict) -> str:
    """Convertit un dictionnaire d'alerte en description textuelle exploitable."""
    return (
        f"Potential DDoS: anomaly_score={alert['anomaly_score']}, "
        f"sttl={alert['sttl']}, Sload={alert['Sload']}, "
        f"sbytes={alert['sbytes']}, dbytes={alert['dbytes']}, "
        f"proto={alert['proto']}, service={alert['service']}"
    )


def test_get_remediation_advice_returns_valid_and_long_advice(fast_advisor, anomaly_description):
    """Verifie que la methode principale retourne un conseil non vide et suffisamment detaille."""
    advice = fast_advisor.get_remediation_advice(anomaly_description)

    assert isinstance(advice, str)
    assert len(advice.strip()) >= 80
    assert "Guidance" in advice or "remediation" in advice.lower()


def test_tfidf_fallback_works_when_huggingface_is_unavailable(monkeypatch):
    """Force l'absence de HuggingFace pour valider l'activation du fallback TF-IDF."""
    docs = [
        Document(page_content="DDoS mitigation with rate-limiting and ACL."),
        Document(page_content="Lateral movement mitigation with segmentation."),
    ]
    captured = {}

    class _FakeFAISS:
        @staticmethod
        def from_documents(documents, embeddings_model):
            captured["documents"] = documents
            captured["embeddings_model"] = embeddings_model
            return {"ok": True}

    original_import = builtins.__import__

    def _patched_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "langchain_community.embeddings":
            raise ImportError("Forced offline mode for test")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(embeddings, "FAISS", _FakeFAISS)
    monkeypatch.setattr(builtins, "__import__", _patched_import)

    with pytest.warns(UserWarning, match="Offline mode: Using TF-IDF embeddings"):
        store = embeddings.build_vector_store(docs)

    assert store == {"ok": True}
    assert len(captured["documents"]) == 2
    assert isinstance(captured["embeddings_model"], embeddings.TFIDFEmbeddings)


def test_realistic_alert_dictionary_can_be_processed(fast_advisor, realistic_alert):
    """Valide qu'une alerte reseau realiste est transformee et traitee sans erreur."""
    description = _alert_to_description(realistic_alert)
    advice = fast_advisor.get_remediation_advice(description)

    assert "sload" in description.lower()
    assert isinstance(advice, str)
    assert len(advice.strip()) > 0


def test_advice_contains_expected_keywords_for_anomaly_type(fast_advisor):
    """Verifie la coherence semantique: DDoS doit produire des mots-cles de mitigation attendus."""
    ddos_query = "DDoS suspected with high Sload traffic flood and packet spike"
    advice = fast_advisor.get_remediation_advice(ddos_query).lower()

    expected_keywords = ["ddos", "rate-limiting", "acl", "scrubbing"]
    assert any(keyword in advice for keyword in expected_keywords)


def test_advisor_response_time_is_under_two_seconds(fast_advisor):
    """Mesure la performance pour garantir une reponse rapide cote experience utilisateur."""
    start = time.perf_counter()
    _ = fast_advisor.get_remediation_advice("Port scan detected on internal subnet")
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0


@pytest.mark.parametrize("description", ["", " ", "a"])
def test_advisor_handles_empty_or_very_short_descriptions(fast_advisor, description):
    """Teste la robustesse sur des entrees faibles: l'advisor ne doit jamais planter."""
    advice = fast_advisor.get_remediation_advice(description)

    assert isinstance(advice, str)
    assert len(advice.strip()) > 0
    if not description.strip():
        assert "FALLBACK REMEDIATION" in advice


def test_advisor_integration_after_knowledge_base_loading(monkeypatch):
    """Valide l'integration: chargement KB puis instanciation/advice de l'advisor."""
    kb_text = load_knowledge_base()
    assert isinstance(kb_text, str)
    assert len(kb_text.strip()) > 0

    class _FakeVectorStore:
        def as_retriever(self, search_kwargs=None):
            return _KeywordAwareRetriever()

    monkeypatch.setattr(advisor, "build_vector_store", lambda docs: _FakeVectorStore())

    rag_advisor = NetworkSecurityAdvisor(top_k=3)
    advice = rag_advisor.get_remediation_advice("Lateral movement detected via SMB scanning")

    assert rag_advisor.retriever is not None
    assert "guidance" in advice.lower() or "remediation" in advice.lower()
