"""TIER 3 — Generative AI (Gemini) with RAG context + student personalisation + multilingual output."""
import json
import os
import time
from datetime import date

from dotenv import load_dotenv

load_dotenv()

LANG_NAMES = {"en": "English", "ml": "Malayalam (മലയാളം)", "hi": "Hindi (हिन्दी)", "ta": "Tamil (தமிழ்)"}
# Tried in order: an overloaded (503), rate-limited (429) or retired (404) model falls through to the next.
MODELS = [m.strip() for m in os.getenv("GEMINI_MODELS", os.getenv("GEMINI_MODEL", "gemini-3.8-flash") +
                                                 ",gemini-3.7-flash,gemini-flash-latest,gemini-3.1-flash-lite").split(",") if m.strip()]
MODEL = MODELS[0]
_client = None


def client():
    global _client
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not key:
        return None
    if _client is None:
        from google import genai
        from google.genai import types
        # Per-request timeout so a slow/overloaded model falls through instead of hanging the UI.
        _client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=int(os.getenv("GEMINI_TIMEOUT_MS", "25000"))))
    return _client


def enabled():
    return client() is not None


def _gen(prompt, parts=None, json_mode=True):
    from google.genai import types
    cfg = types.GenerateContentConfig(temperature=0.2,
                                      response_mime_type="application/json" if json_mode else "text/plain")
    global MODEL
    contents = (parts or []) + [prompt]
    last = None
    for model in dict.fromkeys([MODEL] + MODELS):
        for attempt in range(2):
            try:
                resp = client().models.generate_content(model=model, contents=contents, config=cfg)
                MODEL = model  # remember the one that works
                return resp.text
            except Exception as e:  # noqa: BLE001
                last, msg = e, str(e)
                if "503" in msg and attempt == 0:
                    time.sleep(1.5)
                    continue
                if any(c in msg for c in ("400", "401", "403", "API key")):
                    raise  # bad key / bad request: another model won't help
                break  # overloaded, rate-limited, retired or timed out: try the next model
    raise last


def _parse(txt):
    txt = txt.strip()
    if txt.startswith("```"):
        txt = txt.strip("`").split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(txt)


SUMMARY_PROMPT = """You are a friendly assistant that turns long, formal college circulars into short, clear updates for students.
Today is {today}. Write ALL text values in {lang}. Keep dates in ISO format YYYY-MM-DD. Use simple words a first-year student understands.

STUDENT PROFILE: {profile}

FACTS ALREADY EXTRACTED BY OUR RULE ENGINE (trust these dates/amounts, do not invent new ones):
{facts}

ML CATEGORY GUESS: {category}

RELATED PAST CIRCULARS (for context only — mention if this one updates/changes an earlier one):
{related}

EARLIER VERSION THIS CIRCULAR MAY UPDATE (compare against it):
{previous}

CIRCULAR:
\"\"\"{text}\"\"\"

Return ONLY JSON with this exact shape:
{{
 "title": "max 8 words, catchy, plain",
 "emoji": "one emoji",
 "tldr": "1-2 short sentences: what is happening and what the student must do",
 "key_points": ["3 to 5 short bullet points, each under 15 words"],
 "action_items": [{{"task": "short imperative task", "deadline": "YYYY-MM-DD or null"}}],
 "important_dates": [{{"label": "what happens", "date": "YYYY-MM-DD", "time": "e.g. 10:00 AM or null", "is_deadline": true}}],
 "category": "one of exam|fee|placement|event|holiday|scholarship|hostel|academic",
 "urgency": "high|medium|low",
 "relevant_to_you": {{"verdict": "yes|no|maybe", "reason": "one short sentence addressed to the student"}},
 "penalty": "what happens if ignored, one short sentence, or null",
 "related_note": "one sentence linking to a related past circular, or null",
 "changes": ["if this updates the EARLIER VERSION: each concrete change, e.g. 'Fee deadline moved from 3 Nov to 7 Nov'. Empty list otherwise"]
}}"""


def summarize(text, lang, profile, rules, ml, related, previous=None):
    t0 = time.perf_counter()
    facts = {
        "dates": [{k: d[k] for k in ("date", "time", "context", "is_deadline")} for d in rules["dates"]],
        "amounts": rules["amounts"], "venues": rules["venues"], "links": rules["links"],
        "audience": rules["audience"],
    }
    rel = "\n".join(f"- [{r['category']}] {r['title']}: {r['tldr']}" for r in related) or "none"
    prompt = SUMMARY_PROMPT.format(
        today=date.today().isoformat(), lang=LANG_NAMES.get(lang, "English"),
        profile=json.dumps(profile or {}, ensure_ascii=False), facts=json.dumps(facts, ensure_ascii=False),
        category=f"{ml['category']['label']} ({ml['category']['confidence']})", related=rel, text=text[:12000],
        previous=f"[{previous['title']}]\n{previous['text'][:5000]}" if previous else "none")
    out = _parse(_gen(prompt))
    out["ms"] = round((time.perf_counter() - t0) * 1000)
    out["model"] = MODEL
    return out


def answer(question, lang, profile, docs):
    ctx = "\n\n".join(f"[Notice {i + 1}: {d['title']}]\n{d['text'][:3000]}" for i, d in enumerate(docs))
    prompt = f"""You answer students' questions using ONLY the college notices below. Today is {date.today().isoformat()}.
Student profile: {json.dumps(profile or {}, ensure_ascii=False)}
Answer in {LANG_NAMES.get(lang, 'English')}, in 1-4 short friendly sentences. Mention exact dates/amounts. Cite the notice number like [1].
If the notices don't contain the answer, say so honestly.

NOTICES:
{ctx}

QUESTION: {question}"""
    return _gen(prompt, json_mode=False).strip()


def ocr(data: bytes, mime: str):
    from google.genai import types
    part = types.Part.from_bytes(data=data, mime_type=mime)
    return _gen("Extract all the text from this notice/circular exactly as written. Return plain text only.",
                parts=[part], json_mode=False).strip()
