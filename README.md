# 📋 NoticeLens — Smart Notice Board Summarizer

Turns long, formal college circulars into short, student-friendly updates — in **English, മലയാളം, हिन्दी, தமிழ்**.

## Team Members: 
  1. Abhijith S Unni (Leader)
  2. Joel Lijo Mathew
  3. Ajo Jose
  4. Jairaj R

## Run
```bash
echo "GEMINI_API_KEY=your_key_here" > .env   # optional — app works offline without it
./run.sh                                      # → http://localhost:8000
```

## 3-tier architecture
| Tier | What it does | Tech | Works offline? |
|---|---|---|---|
| ① Rules | Strips boilerplate; extracts dates, deadlines, times, ₹ amounts, venues, links; detects audience (S1–S8, branch); urgency score | Regex + heuristics (`app/rules.py`) | ✅ |
| ② ML | TextRank extractive summary + category classifier (exam/fee/placement/event/…) | TF-IDF, PageRank, LogisticRegression (`app/ml.py`) | ✅ |
| ③ GenAI + RAG | Friendly summary, action checklist, penalty, personal relevance — written directly in the chosen language, grounded on Tier-1 facts + similar past circulars | Gemini + TF-IDF retrieval store (`app/genai_tier.py`, `app/rag.py`) | ❌ → falls back to ①+② |

## Features
- Paste text, upload PDF, or snap a photo of the notice (photo OCR uses Gemini)
- Urgency colour (🔴🟡🟢), category, **"For you / Not for you"** personalisation
- Deadline countdown, ✅ action checklist (saved), ⚠️ penalty if ignored
- 🔊 Read aloud in your language · 📅 Add to calendar (.ics with 1-day reminder) · 💬 WhatsApp share · 📋 Copy
- 🗂️ My Board — all notices sorted by nearest deadline, category filters, "only for me"
- 💬 Ask the notice board — RAG Q&A over every circular, with citations
- 🔁 **What changed** — a new notice is matched (RAG) against earlier ones; moved deadlines, new dates and changed amounts are diffed (`app/diff.py`), plus an AI-written change list. The old notice is marked "Replaced" and drops out of the planner
- 📈 **Task timeline** chart per notice (today → each deadline/event)
- 📊 **Planner** — KPI tiles, top-5 priority tasks across all notices (urgency × days left × relevance), 14-day workload chart, deadline calendar
- 🌙/☀️ Dark & light mode, first-time onboarding (language → semester/branch → try sample)
- "How we summarized this" panel shows each tier's output + timing
- Works with no internet (Tailwind/Alpine bundled locally; AI toggle shows the fallback)
