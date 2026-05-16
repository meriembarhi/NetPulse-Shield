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
'''
from knowledge_base import load_knowledge_base
from embeddings import build_vector_store
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class NetworkSecurityAdvisor:
    def __init__(self, top_k=3):
        raw_text = load_knowledge_base()
        splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
        chunks = splitter.split_text(raw_text)
        docs = [Document(page_content=c) for c in chunks]
        self.vector_store = build_vector_store(docs)
        self.retriever = self.vector_store.as_retriever(search_kwargs={"k": top_k})

    def get_remediation_advice(self, description):
        relevant_docs = self.retriever.invoke(description)
        return "\n\n".join([f"[Guidance {i+1}]\n{d.page_content}" for i, d in enumerate(relevant_docs)])