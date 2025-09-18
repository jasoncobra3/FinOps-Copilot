"""
Simple FAISS retrieval helper.
Functions:
  - load_index_and_meta()
  - retrieve(query, top_k=5)
"""
from pathlib import Path
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_PATH = Path("data/faiss/index.faiss")
META_PATH = Path("data/faiss/meta.json")

# lazy load
_index = None
_meta = None
_model = None

def _load_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def load_index_and_meta():
    global _index, _meta
    if _index is None:
        if not INDEX_PATH.exists() or not META_PATH.exists():
            raise FileNotFoundError("FAISS index or meta.json not found. Run scripts/build_faiss_index.py first.")
        _index = faiss.read_index(str(INDEX_PATH))
    if _meta is None:
        with open(META_PATH, "r", encoding="utf8") as f:
            _meta = json.load(f)
    return _index, _meta

def _embed_query(query):
    model = _load_model()
    emb = model.encode([query], convert_to_numpy=True)
    # normalize
    emb = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-12)
    return emb.astype("float32")

def retrieve(query, top_k=5):
    """
    Returns a list of dicts: {id, score, text, meta}
    """
    index, meta = load_index_and_meta()
    q_emb = _embed_query(query)
    D, I = index.search(q_emb, top_k)
    scores = D[0].tolist()
    indices = I[0].tolist()
    results = []
    for idx, score in zip(indices, scores):
        if idx < 0 or idx >= len(meta):
            continue
        item = meta[idx]
        results.append({
            "id": item.get("id"),
            "score": float(score),
            "text": item.get("text"),
            "meta": item.get("meta")
        })
    return results
