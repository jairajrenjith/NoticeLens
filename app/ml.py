"""TIER 2 — Classical ML. TextRank extractive summary + TF-IDF/LogReg category classifier. Offline."""
import re
import time

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import make_pipeline

from .data import SAMPLES, TRAIN

CATEGORY_EMOJI = {"exam": "📝", "fee": "💰", "placement": "💼", "event": "🎉", "holiday": "🏖️",
                  "scholarship": "🎓", "hostel": "🏠", "academic": "📚"}

_SAMPLE_LABEL = {"fee": "fee", "fee_revised": "fee", "exam": "exam", "placement": "placement", "event": "event"}
_texts = [t for t, _ in TRAIN] + [s["text"] for s in SAMPLES]
_labels = [l for _, l in TRAIN] + [_SAMPLE_LABEL[s["id"]] for s in SAMPLES]
classifier = make_pipeline(
    TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english"),
    LogisticRegression(max_iter=2000, C=8),
).fit(_texts, _labels)

SALIENT = re.compile(r"\d|last date|deadline|must|required|mandatory|register|submit|pay|venue|fine", re.I)


def split_sentences(text: str):
    text = re.sub(r"\b(Rs|No|Ltd|Dr|Mr|Ms|Mrs|Prof|Dept|St|viz|etc|approx)\.", r"\1", text, flags=re.I)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])|\n+", text)
    out = []
    for p in parts:
        p = p.strip(" •-*\t")
        if len(p.split()) < 8 or re.match(r"(sub(ject)?|ref|no)\s*[:.]", p, re.I) or p.upper() == p:
            continue
        out.append(p)
    return out


def textrank(text: str, k: int = 3):
    sents = split_sentences(text)
    if len(sents) <= k:
        return sents, [1.0] * len(sents)
    tfidf = TfidfVectorizer(stop_words="english").fit_transform(sents)
    sim = cosine_similarity(tfidf)
    np.fill_diagonal(sim, 0)
    row = sim.sum(axis=1, keepdims=True)
    row[row == 0] = 1
    m = sim / row
    n, d = len(sents), 0.85
    scores = np.ones(n) / n
    for _ in range(60):  # PageRank power iteration
        scores = (1 - d) / n + d * m.T @ scores
    # Domain boost: sentences carrying dates/obligations matter more to students.
    boost = np.array([1.35 if SALIENT.search(s) else 1.0 for s in sents])
    pos = np.array([1.15 if i < 2 else 1.0 for i in range(n)])  # lead bias
    scores = scores * boost * pos
    top = sorted(np.argsort(-scores)[:k])
    return [sents[i] for i in top], [round(float(scores[i] / scores.max()), 2) for i in top]


def classify(text: str):
    probs = classifier.predict_proba([text])[0]
    order = np.argsort(-probs)
    classes = classifier.classes_
    return {"label": classes[order[0]], "confidence": round(float(probs[order[0]]), 2),
            "top3": [{"label": classes[i], "p": round(float(probs[i]), 2)} for i in order[:3]]}


def run(clean_text: str):
    t0 = time.perf_counter()
    sents, scores = textrank(clean_text, 4)
    cat = classify(clean_text)
    return {
        "key_sentences": sents,
        "sentence_scores": scores,
        "category": cat,
        "emoji": CATEGORY_EMOJI.get(cat["label"], "📌"),
        "ms": round((time.perf_counter() - t0) * 1000, 1),
    }
