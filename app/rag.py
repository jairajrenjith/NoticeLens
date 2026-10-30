"""Lightweight RAG store: past circulars kept in a JSON file, retrieved with TF-IDF cosine similarity."""
import json
import threading
import time
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

STORE_PATH = Path(__file__).parent / "store.json"
_lock = threading.Lock()


def _load():
    if STORE_PATH.exists():
        try:
            return json.loads(STORE_PATH.read_text())
        except json.JSONDecodeError:
            return []
    return []


_docs = _load()


def add(doc_id: str, text: str, title: str, tldr: str, category: str, dates: list, facts: dict | None = None):
    with _lock:
        if any(d["id"] == doc_id for d in _docs):
            return
        _docs.append({"id": doc_id, "text": text, "title": title, "tldr": tldr, "category": category,
                      "dates": dates, "facts": facts or {}, "ts": time.time()})
        STORE_PATH.write_text(json.dumps(_docs, ensure_ascii=False, indent=1))


def search(query: str, k: int = 3, exclude_id: str | None = None, min_score: float = 0.08):
    docs = [d for d in _docs if d["id"] != exclude_id]
    if not docs or not query.strip():
        return []
    vec = TfidfVectorizer(stop_words="english", sublinear_tf=True)
    mat = vec.fit_transform([d["text"] for d in docs] + [query])
    sims = cosine_similarity(mat[-1], mat[:-1])[0]
    ranked = sorted(zip(sims, docs), key=lambda x: -x[0])[:k]
    return [{**{k2: d[k2] for k2 in ("id", "title", "tldr", "category", "dates")}, "facts": d.get("facts", {}), "score": round(float(s), 2),
             "text": d["text"]} for s, d in ranked if s >= min_score]


def count():
    return len(_docs)
