"""
Build FAISS index from docs/finops_tips.md + short billing summaries.
Outputs:
  - data/faiss/index.faiss
  - data/faiss/meta.json
"""
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss
from app.models import engine
from tqdm import tqdm

OUT_DIR = Path("data/faiss")
OUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_NAME = "all-MiniLM-L6-v2"
model = SentenceTransformer(MODEL_NAME)

def load_finops_docs():
    p = Path("docs/finops_tips.md")
    if not p.exists():
        return []
    txt = p.read_text(encoding="utf8")
    # split by blank-line paragraphs
    paras = [s.strip() for s in txt.split("\n\n") if s.strip()]
    texts = []
    for i, p in enumerate(paras, start=1):
        texts.append({
            "id": f"finops_{i}",
            "source": "finops_doc",
            "text": p,
            "meta": {"type": "finops_doc", "paragraph_index": i}
        })
    return texts

def build_billing_chunks():
    # produce one-line summaries per resource-month (or aggregated)
    sql = """
    SELECT b.invoice_month, b.resource_id, b.service, b.resource_group, b.cost, r.owner, r.env
    FROM billing b
    LEFT JOIN resources r ON b.resource_id = r.resource_id
    """
    try:
        df = pd.read_sql_query(sql, engine)
    except Exception as e:
        print("ERROR reading billing/resources:", e)
        return []
    rows = []
    for i, row in df.iterrows():
        rid = str(row.get("resource_id", "unknown"))
        month = str(row.get("invoice_month", "unknown"))
        service = row.get("service", "")
        owner = row.get("owner") if row.get("owner") is not None else "unassigned"
        env = row.get("env") if row.get("env") is not None else "unassigned"
        cost = float(row.get("cost") or 0.0)
        text = f"Resource {rid} ({service}) in {month}: cost {cost:.2f}; owner: {owner}; env: {env}."
        meta = {
            "type": "billing",
            "resource_id": rid,
            "invoice_month": month,
            "service": service,
            "owner": owner,
            "env": env,
            "cost": cost
        }
        rows.append({"id": f"bill_{rid}_{month}", "source": "billing", "text": text, "meta": meta})
    return rows

def encode_texts(texts, batch_size=64):
    raw_texts = [t["text"] for t in texts]
    embeddings = model.encode(raw_texts, show_progress_bar=True, batch_size=batch_size, convert_to_numpy=True)
    # normalize to unit vectors for cosine via inner-product index
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / (norms + 1e-12)
    return embeddings

def main():
    print("Loading docs and billing...")
    doc_chunks = load_finops_docs()
    bill_chunks = build_billing_chunks()
    all_chunks = doc_chunks + bill_chunks
    if not all_chunks:
        print("No chunks found. Ensure docs/finops_tips.md exists and billing table populated.")
        return

    print(f"Total chunks: {len(all_chunks)}")
    embs = encode_texts(all_chunks)
    dim = embs.shape[1]
    print("Creating FAISS index (IndexFlatIP)... dim=", dim)
    index = faiss.IndexFlatIP(dim)
    index.add(embs.astype("float32"))
    faiss.write_index(index, str(OUT_DIR / "index.faiss"))
    print("Saved index to", OUT_DIR / "index.faiss")

    # Save meta
    meta = [{"id": c["id"], "source": c["source"], "text": c["text"], "meta": c["meta"]} for c in all_chunks]
    with open(OUT_DIR / "meta.json", "w", encoding="utf8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print("Saved metadata to", OUT_DIR / "meta.json")
    print("DONE")

if __name__ == "__main__":
    main()
