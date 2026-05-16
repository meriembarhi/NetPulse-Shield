"""
embeddings.py - Vector Engine with offline TF-IDF fallback
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
        if not self._fitted:
            self._fit(texts)
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
