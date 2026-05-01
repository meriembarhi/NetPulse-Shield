"""
embeddings.py - The "Translator" & Offline Support

This module translates the security manual into a mathematical format that the AI can 
search through lightning-fast. It also includes a "smart fallback": if 
your internet is down, it automatically switches to a simpler method so 
the system never stops protecting your network.


This module is the Mathematical Core of the RAG system. It handles the transformation of 
natural language into high-dimensional vectors, enabling the computer to perform complex 
"semantic" searches that understand context rather than just matching keywords.  

Key Technical Operations:

Semantic Vectorization: It utilizes Sentence-Transformer models to convert security guides into
numerical "embeddings". This allows the AI to recognize that "traffic flood" and 
"volumetric attack" are conceptually the same thing.  

Resilient Fallback Mechanism: 
To ensure High Availability, the module includes a local TF-IDF fallback. If an internet 
connection is unavailable, the system automatically switches to this internal mathematical 
method to remain 100% functional offline.  

Similarity Optimization: It prepares the data for the FAISS index, ensuring that the most 
relevant security advice can be retrieved with near-zero latency.
"""

import numpy as np
import warnings
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS

class TFIDFEmbeddings(Embeddings):
    def __init__(self, max_features=4096):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self._vectorizer = TfidfVectorizer(max_features=max_features)
        self._fitted = False

    def _fit(self, texts):
        self._vectorizer.fit(texts)
        self._fitted = True

    def embed_documents(self, texts):
        if not self._fitted: self._fit(texts)
        matrix = self._vectorizer.transform(texts).toarray().astype(np.float32)
        return (matrix / np.linalg.norm(matrix, axis=1, keepdims=True)).tolist()

    def embed_query(self, text):
        vec = self._vectorizer.transform([text]).toarray().astype(np.float32)[0]
        return (vec / np.linalg.norm(vec)).tolist()

def build_vector_store(documents, model_name="all-MiniLM-L6-v2"):
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name=model_name)
        embeddings.embed_query("test")
    except Exception:
        warnings.warn("Offline mode: Using TF-IDF embeddings.")
        tfidf = TFIDFEmbeddings()
        tfidf.embed_documents([doc.page_content for doc in documents])
        embeddings = tfidf
    return FAISS.from_documents(documents, embeddings)