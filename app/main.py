"""NoticeLens API — 3-tier pipeline: Rules → ML → GenAI(+RAG). Run: uvicorn app.main:app --reload"""
import hashlib
import io
import re
import time
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import genai_tier, ml, rag, rules
from .data import SAMPLES

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="NoticeLens")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class SummarizeReq(BaseModel):
    text: str
    lang: str = "en"
    profile: dict | None = None
    use_ai: bool = True


class AskReq(BaseModel):
    question: str
    lang: str = "en"
    profile: dict | None = None
    use_ai: bool = True


def doc_id(text):
    return hashlib.sha1(text.strip().encode()).hexdigest()[:10]


def offline_title(clean_text, raw):
    m = re.search(r"^\s*(?:sub(?:ject)?|re)\s*[:.\-]\s*(.+)$", raw, re.I | re.M)
    if m:
        t = re.sub(r"\s*[–-]\s*reg\.?$", "", m.group(1).strip(), flags=re.I)
        return t[:80]
    for line in clean_text.split("\n")[:4]:
        line = line.strip()
        if 2 <= len(line.split()) <= 9 and line.upper() != line and not line.endswith(".") and not re.search(r"\d{2}/\d{2}", line):
            return line
    q = re.search(r'["“]([^"”]{3,40})["”]', clean_text)
    if q:
        return q.group(1)
    first = ml.split_sentences(clean_text)
    words = (first[0] if first else clean_text).split()
    return " ".join(words[:9]) + ("…" if len(words) > 9 else "")


def merge(r, m, ai, raw):
    """Build the student-facing card. AI fields win when present; rules/ML are fallback + grounding."""
    rule_dates = [{"label": d["context"], "date": d["date"], "time": d["time"], "is_deadline": d["is_deadline"]}
                  for d in r["dates"]]
    if ai:
        dates = ai.get("important_dates") or rule_dates
        return {
            "source": "ai",
            "title": ai.get("title") or offline_title(r["clean_text"], raw),
            "emoji": ai.get("emoji") or m["emoji"],
            "tldr": ai.get("tldr", ""),
            "key_points": ai.get("key_points", []),
            "actions": [a if isinstance(a, dict) else {"task": a, "deadline": None} for a in ai.get("action_items", [])],
            "dates": dates,
            "category": ai.get("category") or m["category"]["label"],
            "urgency": ai.get("urgency") or r["urgency"]["level"],
            "relevance": ai.get("relevant_to_you") or r["relevance"],
            "penalty": ai.get("penalty"),
            "related_note": ai.get("related_note"),
        }
    title = offline_title(r["clean_text"], raw)
    title = title[:1].upper() + title[1:]
    body = [s for s in m["key_sentences"] if s.strip() != title.strip()]
    return {
        "source": "offline",
        "title": title,
        "emoji": m["emoji"],
        "tldr": rules.tidy(body[0] if body else r["clean_text"][:200]),
        "key_points": [rules.tidy(b) for b in (body[1:] if len(body) > 2 else body)],
        "actions": [{"task": a, "deadline": next((d["date"] for d in rules.extract_dates(a)), None)} for a in r["actions"][:4]],
        "dates": rule_dates,
        "category": m["category"]["label"],
        "urgency": r["urgency"]["level"],
        "relevance": r["relevance"],
        "penalty": None,
        "related_note": None,
    }


def pipeline(text, lang="en", profile=None, use_ai=True, store=True):
    did = doc_id(text)
    r = rules.run(text, profile)
    m = ml.run(r["clean_text"])
    t0 = time.perf_counter()
    related = rag.search(r["clean_text"], k=3, exclude_id=did)
    rag_ms = round((time.perf_counter() - t0) * 1000, 1)
    ai, ai_error = None, None
    if use_ai and genai_tier.enabled():
        try:
            ai = genai_tier.summarize(r["clean_text"], lang, profile, r, m, related)
        except Exception as e:  # noqa: BLE001 — any AI failure falls back to tiers 1+2
            ai_error = f"{type(e).__name__}: {str(e)[:200]}"
    elif use_ai:
        ai_error = "No GEMINI_API_KEY configured"
    summary = merge(r, m, ai, text)
    if store:
        rag.add(did, r["clean_text"], summary["title"], summary["tldr"], summary["category"],
                [d["date"] for d in summary["dates"]])
    summary_words = len((summary["tldr"] + " " + " ".join(summary["key_points"])).split())
    return {
        "id": did, "lang": lang, "summary": summary,
        "stats": {"original_words": r["word_count"], "summary_words": summary_words,
                  "read_time_saved_s": max(0, round((r["word_count"] - summary_words) / 3.5))},
        "related": [{k: x[k] for k in ("id", "title", "tldr", "category", "score")} for x in related],
        "tiers": {
            "rules": {k: v for k, v in r.items() if k != "clean_text"},
            "ml": m,
            "rag": {"matches": len(related), "ms": rag_ms, "store_size": rag.count()},
            "ai": ai, "ai_error": ai_error,
        },
    }


@app.on_event("startup")
def seed():
    for s in SAMPLES:  # seed the RAG store so 'Ask' and 'related' work from the first click
        pipeline(s["text"], use_ai=False)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {"ai_enabled": genai_tier.enabled(), "model": genai_tier.MODEL, "store_size": rag.count()}


@app.get("/api/samples")
def samples():
    return SAMPLES


@app.post("/api/summarize")
def summarize(req: SummarizeReq):
    if len(req.text.strip()) < 40:
        raise HTTPException(400, "Please paste a longer circular (at least a couple of sentences).")
    return pipeline(req.text, req.lang, req.profile, req.use_ai)


@app.post("/api/extract")
async def extract(file: UploadFile = File(...)):
    data = await file.read()
    name, mime = (file.filename or "").lower(), file.content_type or ""
    if name.endswith(".pdf") or mime == "application/pdf":
        from pypdf import PdfReader
        text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        if text.strip():
            return {"text": text, "method": "pdf"}
        if not genai_tier.enabled():
            raise HTTPException(422, "This PDF is scanned (no text layer). Add a Gemini key for OCR.")
        return {"text": genai_tier.ocr(data, "application/pdf"), "method": "ai-ocr"}
    if mime.startswith("image/"):
        if not genai_tier.enabled():
            raise HTTPException(422, "Reading photos needs the AI tier (Gemini key).")
        return {"text": genai_tier.ocr(data, mime), "method": "ai-ocr"}
    if name.endswith(".txt") or mime.startswith("text/"):
        return {"text": data.decode("utf-8", "ignore"), "method": "text"}
    raise HTTPException(415, "Upload a PDF, image or .txt file.")


@app.post("/api/ask")
def ask(req: AskReq):
    docs = rag.search(req.question, k=4, min_score=0.02)
    if not docs:
        return {"answer": None, "sources": []}
    sources = [{"id": d["id"], "title": d["title"], "category": d["category"]} for d in docs]
    if req.use_ai and genai_tier.enabled():
        try:
            return {"answer": genai_tier.answer(req.question, req.lang, req.profile, docs), "sources": sources,
                    "source": "ai"}
        except Exception:  # noqa: BLE001
            pass
    # Offline: best-matching sentences from the top notice.
    sents = ml.split_sentences(docs[0]["text"])
    best = rag_sentences(req.question, sents)
    return {"answer": " ".join(rules.tidy(b) for b in best), "sources": sources[:1], "source": "offline"}


def rag_sentences(q, sents, k=2):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    if not sents:
        return []
    mat = TfidfVectorizer(stop_words="english").fit_transform(sents + [q])
    sims = cosine_similarity(mat[-1], mat[:-1])[0]
    return [sents[i] for i in sorted(sims.argsort()[::-1][:k])]
