# advisor.py
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