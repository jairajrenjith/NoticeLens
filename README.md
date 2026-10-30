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
- 🌙/☀️ Dark & light mode, first-time onboarding (language → semester/branch → try sample)
- "How we summarized this" panel shows each tier's output + timing
- Works with no internet (Tailwind/Alpine bundled locally; AI toggle shows the fallback)

## 3-min demo script
1. Fresh browser (or click **?**) → pick മലയാളം → S5 · CSE → "Try a sample" → fee circular becomes a red card: "4 days left".
2. Switch language to Hindi → summary re-generates in Hindi. Tap 🔊 Listen.
3. Open "How we summarized this" → show the three tiers + timings.
4. Toggle **AI off** → summarize again → still works (Rules + ML). "That's why we built 3 tiers."
5. Try the placement sample → "🚫 Not for you — meant for S7".
6. My Board → sorted by deadline. Ask → "When is the fee deadline?" → answer with citation.
