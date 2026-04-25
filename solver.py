"""
solver.py - RAG-based Network Security Remediation Advisor for NetPulse-Shield

Uses LangChain with a local FAISS vector store and sentence-transformer
embeddings to retrieve contextually relevant remediation steps for
detected network anomalies — no external API key required.

Workflow
--------
1.  A text knowledge base of security remediation guides is loaded
    (from ``docs/remediation_knowledge.txt`` or the built-in fallback).
2.  The documents are split into chunks and embedded with either a
    sentence-transformers model (``all-MiniLM-L6-v2`` by default, requires
    internet on first use) or a local TF-IDF fallback when offline.
3.  Given an anomaly description, the retriever finds the most relevant
    chunks and a prompt template assembles them into actionable advice.
4.  When an optional LLM pipeline is supplied, a full LCEL chain is built
    to synthesise the retrieved context into a coherent answer.
"""

import textwrap
import warnings
from pathlib import Path
from typing import List

import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ---------------------------------------------------------------------------
# Offline-capable TF-IDF embeddings (no internet required)
# ---------------------------------------------------------------------------


class TFIDFEmbeddings(Embeddings):
    """
    Lightweight TF-IDF based embeddings backed by scikit-learn.

    Fits a ``TfidfVectorizer`` on all documents during initialisation so
    that subsequent query embeddings are in the same vector space.  Dense
    float32 vectors are returned, making them compatible with FAISS.
    """

    def __init__(self, max_features: int = 4096):
        """
        Initialise the TF-IDF vectorizer.

        Parameters
        ----------
        max_features : int
            Maximum number of TF-IDF features (vocabulary size) to extract.
            Higher values capture more vocabulary at the cost of larger
            embedding vectors and more memory.
        """
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(
            max_features=max_features,
            sublinear_tf=True,
            strip_accents="unicode",
            analyzer="word",
            ngram_range=(1, 2),
        )
        self._fitted = False

    def _fit(self, texts: List[str]) -> None:
        self._vectorizer.fit(texts)
        self._fitted = True

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self._fitted:
            self._fit(texts)
        matrix = self._vectorizer.transform(texts).toarray().astype(np.float32)
        # L2-normalise so cosine similarity ≈ dot-product (FAISS default)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return (matrix / norms).tolist()

    def embed_query(self, text: str) -> List[float]:
        if not self._fitted:
            raise RuntimeError("Call embed_documents first to fit the vectorizer.")
        vec = self._vectorizer.transform([text]).toarray().astype(np.float32)[0]
        norm = np.linalg.norm(vec)
        return (vec / norm if norm > 0 else vec).tolist()


# ---------------------------------------------------------------------------
# Built-in knowledge base (used when docs/remediation_knowledge.txt is absent)
# ---------------------------------------------------------------------------

_BUILTIN_KNOWLEDGE = """
# DDoS Attack Remediation
A Distributed Denial-of-Service (DDoS) attack floods a target with traffic
to exhaust its resources and make it unavailable to legitimate users.

Indicators: Sudden spike in packets_per_second, high bytes_sent from many
source IPs, very short connection durations combined with maximum packet sizes.

Remediation steps:
1. Enable rate-limiting on edge routers and firewalls immediately.
2. Activate upstream scrubbing services (e.g., Cloudflare Magic Transit,
   AWS Shield Advanced) to absorb volumetric traffic.
3. Use anycast routing or a CDN to distribute and absorb the load.
4. Apply access control lists (ACLs) to block the source IP ranges.
5. Alert the upstream ISP for null-routing assistance on heavily abused prefixes.
6. Scale out horizontally (auto-scaling groups) to absorb residual traffic.
7. After mitigation, collect NetFlow/IPFIX logs and submit to threat-intel feeds.

---

# Port Scan Detection and Remediation
A port scan probes a host across many destination ports to discover open
services that can be exploited.

Indicators: Single source IP connecting to many distinct dst_port values in
a short duration, small packet_size (often just SYN packets), low bytes_sent.

Remediation steps:
1. Block the scanning source IP at the perimeter firewall.
2. Enable port-scan detection in your IDS/IPS (e.g., Snort, Suricata rule
   ``spp_portscan`` or ``portscan`` preprocessor).
3. Close or firewall off all non-essential ports; follow the principle of
   least privilege for network exposure.
4. Move management interfaces (SSH, RDP) to non-standard ports and restrict
   to known management CIDR ranges.
5. Enable SYN cookies on Linux hosts (``sysctl -w net.ipv4.tcp_syncookies=1``)
   to protect against SYN-flood variants.
6. Review the targeted host for unnecessary open services and patch them.

---

# Data Exfiltration Remediation
Data exfiltration occurs when large volumes of sensitive data are transferred
out of the network to an unauthorised destination.

Indicators: Unusually high bytes_sent to external IPs, long-duration sessions
at unusual hours, connections to known data-sink IP ranges or cloud storage.

Remediation steps:
1. Immediately isolate the suspected endpoint from the network.
2. Block outbound traffic to the destination IP/domain at the firewall.
3. Capture and preserve network forensic evidence (PCAP, NetFlow).
4. Enable Data Loss Prevention (DLP) policies on egress proxies.
5. Rotate credentials (API keys, passwords, certificates) for all services
   accessible from the compromised host.
6. Conduct a full endpoint forensic investigation (memory dump, disk image).
7. Notify affected parties per your incident-response plan and regulatory
   obligations (GDPR, HIPAA, etc.).

---

# Brute-Force Login Attack Remediation
Repeated failed authentication attempts targeting SSH, RDP, or web login
endpoints indicate a brute-force or credential-stuffing attack.

Indicators: High packets_per_second to a single dst_port (22, 3389, 80/443),
many short connections from one or a few source IPs.

Remediation steps:
1. Temporarily ban the source IP using fail2ban or similar tooling.
2. Enforce multi-factor authentication (MFA) on all remote-access services.
3. Replace password authentication with public-key authentication for SSH.
4. Implement account-lockout policies after N failed attempts.
5. Deploy a CAPTCHA or bot-management solution for web login pages.
6. Move SSH to a non-standard port and restrict it to a VPN or bastion host.
7. Review logs for successful logins immediately after the burst to check for
   compromise; reset any affected credentials.

---

# Man-in-the-Middle (MitM) Attack Remediation
A MitM attack intercepts communication between two parties to eavesdrop
or modify traffic.

Indicators: ARP spoofing alerts, unexpected certificate changes, unusual
traffic routing through intermediate hosts, duplicate MAC-IP mappings.

Remediation steps:
1. Enable Dynamic ARP Inspection (DAI) on managed switches.
2. Deploy HTTPS everywhere with HSTS (HTTP Strict Transport Security) and
   certificate pinning for critical applications.
3. Use mutual TLS (mTLS) for service-to-service communication.
4. Enable DNSSEC and DNS-over-HTTPS (DoH) to prevent DNS spoofing.
5. Segment the network with VLANs and restrict inter-VLAN routing.
6. Monitor for duplicate ARP entries and abnormal routing-table changes.
7. Educate users to verify certificate warnings and report anomalies.

---

# Ransomware Network Activity Remediation
Ransomware often exhibits lateral-movement traffic before encryption,
including SMB scanning, credential harvesting, and C2 beaconing.

Indicators: Internal SMB (port 445) scanning traffic, beaconing to external
IPs at regular intervals (periodic anomaly_score spikes), large encrypted
outbound transfers.

Remediation steps:
1. Immediately isolate affected hosts at the network level (VLAN quarantine).
2. Disable SMBv1 across the environment (``Set-SmbServerConfiguration
   -EnableSMB1Protocol $false`` on Windows).
3. Block outbound traffic to identified C2 IP/domain indicators.
4. Restore affected systems from verified clean backups — do NOT pay ransom.
5. Patch the initial infection vector (phishing gateway, unpatched software).
6. Conduct a full incident-response investigation before reconnecting hosts.
7. Implement network micro-segmentation to limit lateral movement in future.

---

# General Network Security Best Practices
Apply these baseline controls to reduce attack surface across all threats:

- Keep all software, firmware, and OS packages up to date.
- Follow the principle of least privilege for user and service accounts.
- Enable logging (syslog, NetFlow, PCAP retention) and centralise in a SIEM.
- Conduct regular penetration testing and vulnerability assessments.
- Train staff on phishing awareness and secure-coding practices.
- Maintain and rehearse an incident response plan.
- Implement network segmentation and zero-trust architecture.
- Use encrypted protocols (TLS 1.2+, SSH, SFTP) for all data in transit.
"""


# ---------------------------------------------------------------------------
# Advisor class
# ---------------------------------------------------------------------------


class NetworkSecurityAdvisor:
    """
    RAG-based advisor that retrieves and formats remediation guidance.

    Parameters
    ----------
    knowledge_base_path : str | None
        Path to a plain-text knowledge base file.  Falls back to the
        built-in knowledge base when *None* or the file is not found.
    embedding_model : str
        Name of a sentence-transformers model used to embed documents
        and queries.
    top_k : int
        Number of document chunks to retrieve per query.
    llm_pipeline : transformers.Pipeline | None
        Optional Hugging Face text-generation pipeline.  When *None*,
        the advisor returns retrieved chunks directly without an LLM
        synthesis step.
    """

    def __init__(
        self,
        knowledge_base_path: str | None = None,
        embedding_model: str = "all-MiniLM-L6-v2",
        top_k: int = 3,
        llm_pipeline=None,
    ):
        self.top_k = top_k
        self._llm_pipeline = llm_pipeline

        raw_text = self._load_knowledge_base(knowledge_base_path)
        documents = self._split_documents(raw_text)
        self.vector_store = self._build_vector_store(documents, embedding_model)
        self.retriever = self.vector_store.as_retriever(
            search_kwargs={"k": self.top_k}
        )

        if llm_pipeline is not None:
            self._lcel_chain = self._build_lcel_chain(llm_pipeline)
        else:
            self._lcel_chain = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_knowledge_base(path: str | None) -> str:
        """Return raw knowledge-base text from file or built-in fallback."""
        if path and Path(path).is_file():
            return Path(path).read_text(encoding="utf-8")
        fallback_path = Path("docs") / "remediation_knowledge.txt"
        if fallback_path.is_file():
            return fallback_path.read_text(encoding="utf-8")
        return _BUILTIN_KNOWLEDGE

    @staticmethod
    def _split_documents(text: str) -> list[Document]:
        """Split raw text into overlapping chunks for dense retrieval."""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=80,
            separators=["\n---\n", "\n\n", "\n", " "],
        )
        chunks = splitter.split_text(text)
        return [Document(page_content=chunk) for chunk in chunks]

    @staticmethod
    def _build_vector_store(
        documents: list[Document], model_name: str
    ) -> FAISS:
        """
        Embed documents and build an in-memory FAISS index.

        Attempts to use HuggingFace sentence-transformers first; falls back
        to the local TF-IDF embedder when the model cannot be downloaded
        (e.g., in an offline / sandboxed environment).
        """
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings

            embeddings = HuggingFaceEmbeddings(model_name=model_name)
            # probe with a single string to catch download errors early
            embeddings.embed_query("test")
        except Exception:
            warnings.warn(
                "HuggingFace embeddings unavailable (offline?). "
                "Falling back to local TF-IDF embeddings.",
                stacklevel=2,
            )
            tfidf = TFIDFEmbeddings()
            # Fit on all document texts so embed_query works later
            texts = [doc.page_content for doc in documents]
            tfidf.embed_documents(texts)
            embeddings = tfidf

        return FAISS.from_documents(documents, embeddings)

    def _build_lcel_chain(self, llm_pipeline):
        """
        Build a LangChain Expression Language (LCEL) RAG chain.

        Wraps the supplied Hugging Face pipeline with LangChain's
        ``HuggingFacePipeline`` wrapper and composes:
        retriever → prompt → LLM → string output parser.
        """
        from langchain_community.llms import HuggingFacePipeline

        llm = HuggingFacePipeline(pipeline=llm_pipeline)
        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template=textwrap.dedent(
                """\
                You are a network security expert.  Use ONLY the context below to
                recommend remediation steps for the described anomaly.

                Context:
                {context}

                Anomaly description:
                {question}

                Remediation advice:"""
            ),
        )

        def _format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        return (
            {
                "context": self.retriever | _format_docs,
                "question": RunnablePassthrough(),
            }
            | prompt
            | llm
            | StrOutputParser()
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_remediation_advice(self, anomaly_description: str) -> str:
        """
        Return remediation advice for the given anomaly description.

        When an LLM pipeline was provided at construction time, the
        retrieved chunks are synthesised into a coherent answer.
        Otherwise, the raw retrieved chunks are returned.

        Parameters
        ----------
        anomaly_description : str
            Free-text description of the detected anomaly (e.g. output
            from the detector or a human analyst).

        Returns
        -------
        str
            Formatted remediation guidance.
        """
        relevant_docs = self.retriever.invoke(anomaly_description)

        if self._lcel_chain is not None:
            return self._lcel_chain.invoke(anomaly_description).strip()

        # Retrieval-only mode: concatenate the relevant chunks
        sections = []
        for i, doc in enumerate(relevant_docs, start=1):
            sections.append(f"[Relevant guidance {i}]\n{doc.page_content.strip()}")
        return "\n\n".join(sections)

    def advise_on_anomalies(self, anomaly_df) -> list[dict]:
        """
        Generate remediation advice for each row flagged as anomalous.

        Parameters
        ----------
        anomaly_df : pd.DataFrame
            A DataFrame whose rows each represent one detected anomaly.
            Any columns present are converted to a description string.

        Returns
        -------
        list[dict]
            Each element has keys ``index``, ``description``, and
            ``advice``.
        """
        results = []
        for idx, row in anomaly_df.iterrows():
            description = "Network anomaly detected with the following characteristics: " + ", ".join(
                f"{col}={val:.2f}" if isinstance(val, float) else f"{col}={val}"
                for col, val in row.items()
                if col not in ("anomaly", "anomaly_score", "is_anomaly")
            )
            advice = self.get_remediation_advice(description)
            results.append(
                {"index": idx, "description": description, "advice": advice}
            )
        return results


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import sys

    print("NetPulse-Shield — RAG-based Security Advisor")
    print("=" * 50)

    print("Initialising knowledge base and embeddings …")
    advisor = NetworkSecurityAdvisor()
    print("Ready.\n")

    # Accept an optional anomaly description from the command line
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = (
            "High packets_per_second (450) with large bytes_sent (48000) "
            "from a single source IP to random destination ports — "
            "possible DDoS attack."
        )

    print(f"Query: {query}\n")
    print("Remediation Advice")
    print("-" * 50)
    advice = advisor.get_remediation_advice(query)
    print(advice)
