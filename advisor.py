'''
This module serves as the Logic Engine for the NetPulse-Shield remediation system.
It implements a Retrieval-Augmented Generation (RAG) workflow to bridge the gap between 
raw technical data and human-readable security guidance.  

Key Technical Operations:

Semantic Search: Instead of just looking for matching words, this module uses vector 
similarity search to understand the "meaning" of a network threat.  

Context Retrieval: It acts as a specialized Matchmaker, querying a high-performance 
FAISS index to extract the most relevant mitigation strategies from the knowledge base.

System Orchestration: It coordinates the flow of information between the Knowledge Base
(the data source) and the Embeddings (the mathematical representation), ensuring the system 
provides accurate, expert-level "treatments" for any detected network "symptoms".  

Fallback Resilience: When the vector store is thin or unreachable, the system gracefully
returns a generic but actionable remediation fallback.
'''
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from knowledge_base import load_knowledge_base
from embeddings import build_vector_store


class NetworkSecurityAdvisor:
    def __init__(self, top_k: int = 3):
        self.top_k = top_k
        self.retriever = None
        self.vector_store = None
        self._initialize_vector_store()

    def _initialize_vector_store(self) -> None:
        """Initialize the vector store with fallback handling."""
        try:
            raw_text = load_knowledge_base()
            if not raw_text or len(raw_text.strip()) == 0:
                raise ValueError("Knowledge base is empty.")
            
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=600, chunk_overlap=80
            )
            chunks = splitter.split_text(raw_text)
            
            if not chunks:
                raise ValueError("No chunks produced from knowledge base.")
            
            docs = [Document(page_content=c) for c in chunks]
            self.vector_store = build_vector_store(docs)
            self.retriever = self.vector_store.as_retriever(
                search_kwargs={"k": self.top_k}
            )
        except Exception as e:
            print(f"⚠️  Warning: Failed to initialize vector store: {e}")
            print("   System will use fallback remediation for all queries.")
            self.retriever = None

    def get_remediation_advice(self, description: str) -> str:
        """
        Retrieve remediation advice for a given threat description.
        Falls back to generic advice if the vector store is unavailable.
        
        Args:
            description: The threat or anomaly description.
        
        Returns:
            A formatted remediation report with source attribution.
        """
        if not description or len(description.strip()) == 0:
            return self._fallback_advice("Unknown threat")
        
        if self.retriever is None:
            return self._fallback_advice(description)
        
        try:
            relevant_docs = self.retriever.invoke(description)
            
            if not relevant_docs:
                return self._fallback_advice(description)
            
            return self._format_advice_with_scores(relevant_docs, description)
        except Exception as e:
            print(f"⚠️  Warning: Retrieval failed: {e}. Using fallback.")
            return self._fallback_advice(description)

    def _format_advice_with_scores(
        self, docs: List[Document], query: str
    ) -> str:
        """Format retrieved documents with attribution and confidence."""
        output = []
        
        for i, doc in enumerate(docs, 1):
            output.append(f"[Guidance {i}]")
            output.append(doc.page_content)
            output.append("")  # Blank line for readability
        
        output.append("---")
        output.append(f"ℹ️  Remediation retrieved from knowledge base ({len(docs)} sources)")
        output.append(f"   Query: \"{query[:60]}...\"" if len(query) > 60 else f"   Query: \"{query}\"")
        
        return "\n".join(output)

    def _fallback_advice(self, threat: str) -> str:
        """Provide a generic but actionable fallback remediation."""
        return f"""
⚠️  FALLBACK REMEDIATION (Knowledge base unavailable)

Threat Detected: {threat}

IMMEDIATE MITIGATION STEPS:
1. Isolate affected systems from the network if the threat severity is high.
2. Enable detailed logging on affected hosts and network devices.
3. Apply rate-limiting or IP-level filtering if volumetric attacks are detected.
4. Review firewall rules and ACLs on edge routers.
5. Consult your organization's incident response playbook.

INVESTIGATIVE ACTIONS:
- Collect packet captures for forensic analysis.
- Check for lateral movement indicators in network logs.
- Verify integrity of critical services and data.
- Document timeline and affected assets.

CONTACT: Escalate to your Security Operations Center (SOC) for expert review.

---
ℹ️  This is a generic fallback. For precise guidance, rebuild the knowledge base.
"""
