"""TIER 1 — Rule-based extraction. Instant, deterministic, works fully offline."""
import re
from datetime import date, datetime

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MON = r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"

DATE_PATTERNS = [
    # 30 October 2026 / 30th Oct, 2026 / 30 Oct
    (re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\b\s*(?:of\s+)?{MON}\.?,?\s*(\d{{4}})?", re.I), "dmy"),
    # October 30, 2026 / Oct 30th
    (re.compile(rf"\b{MON}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?\b(?!\d),?\s*(\d{{4}})?", re.I), "mdy"),
    # 30/10/2026, 30-10-26, 30.10.2026
    (re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})\b"), "num"),
]
TIME_RE = re.compile(r"\b(\d{1,2}(?::|\.)\d{2}\s*(?:am|pm|a\.m\.|p\.m\.)?|\d{1,2}\s*(?:am|pm|a\.m\.|p\.m\.))", re.I)
AMOUNT_RE = re.compile(r"(?:₹|rs\.?|inr)\s*(\d[\d,]*\d|\d)(?:\s*/-)?", re.I)
URL_RE = re.compile(r"https?://[^\s)>\]]+|www\.[^\s)>\]]+", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{9}\b")
VENUE_RE = re.compile(r"(?:venue|location|place)\s*[:\-]\s*([^\n.;]+)", re.I)
VENUE_AT_RE = re.compile(r"\b(?:at|in)\s+(?:the\s+)?([A-Z][\w&]*(?:\s+[A-Z][\w&]*)*\s+(?:Hall|Auditorium|Lab|Block|Room|Ground|Seminar Hall|Library))", re.M)

DEADLINE_HINTS = re.compile(
    r"last date|final date|on or before|deadline|due date|before|not later than|closes?|until|till|latest by", re.I)

URGENCY_WORDS = {
    "high": ["urgent", "mandatory", "compulsory", "immediately", "strictly", "fine", "penalty",
             "debarred", "will not be permitted", "not be allowed", "last date", "final", "without fail",
             "deadline", "absent", "cancelled", "postponed", "rescheduled"],
    "medium": ["required", "must", "should", "kindly", "requested", "register", "submit", "pay",
               "attendance", "exam", "examination", "fee"],
}

ACTION_RE = re.compile(
    r"\b(must|should|are (?:required|requested|directed|instructed|advised) to|required to|kindly|"
    r"submit|register|pay|bring|report|carry|apply|fill|upload|attend|collect|contact|ensure)\b", re.I)

BOILERPLATE = re.compile(
    r"^\s*(dear\s+(students|all|parents|sir|madam).*|greetings.*|regards,?|warm regards,?|thanking you.*|"
    r"thank you.*|yours (sincerely|faithfully),?|sd/-.*|copy to.*|forwarded.*|\(?signature\)?|"
    r"principal|registrar|dean.*|.*@.*\.(com|in|org|edu).*|mobile\s*:.*|ph(one)?\s*:.*|https?://\S+\s*,?.*)$",
    re.I)

BRANCHES = {
    "CSE": r"\b(cse|cs|computer science)\b",
    "ECE": r"\b(ece|ec|electronics(?: and| &) communication)\b",
    "EEE": r"\b(eee|ee|electrical)\b",
    "ME": r"\b(me|mech|mechanical)\b",
    "CE": r"\b(ce|civil)\b",
    "IE": r"\b(ie|industrial)\b",
    "AE": r"\b(ae|applied electronics)\b",
    "ARCH": r"\b(arch|architecture|b\.arch)\b",
}
YEAR_TO_SEMS = {"first": ["S1", "S2"], "1st": ["S1", "S2"], "second": ["S3", "S4"], "2nd": ["S3", "S4"],
                "third": ["S5", "S6"], "3rd": ["S5", "S6"], "fourth": ["S7", "S8"], "final": ["S7", "S8"],
                "4th": ["S7", "S8"]}


def clean(text: str) -> str:
    lines = [l.rstrip() for l in text.replace("\r", "").split("\n")]
    kept = []
    for l in lines:
        l = l.strip()
        if not l:
            continue
        if BOILERPLATE.match(l) and len(l.split()) <= 12:
            continue
        # Long single-line notices: strip greeting prefix / sign-off suffix instead of dropping the line.
        l = re.sub(r"^(dear\s+\w+|greetings[^,.!]*)[,!.]?\s*", "", l, flags=re.I)
        l = re.sub(r"\s*(regards|thanking you|yours (sincerely|faithfully)|thank you)\b[\s\S]{0,80}$", "", l, flags=re.I)
        if l:
            kept.append(l)
    out = "\n".join(kept)
    return re.sub(r"[ \t]+", " ", out).strip()


def _year(y, today):
    if not y:
        return today.year
    y = int(y)
    return y + 2000 if y < 100 else y


ABBR = re.compile(r"\b(Rs|No|Ltd|Dr|Mr|Ms|Mrs|Prof|Dept|St|viz|etc|approx)\.", re.I)
PREAMBLE = re.compile(r"^(it is hereby (informed|notified|intimated) that|this is to (inform|notify) (you |all )?that|"
                      r"we are (pleased|happy) to (inform you that|announce)|all are hereby informed that|kindly note that)\s*",
                      re.I)


def tidy(sent: str) -> str:
    sent = PREAMBLE.sub("", sent.strip())
    return sent[:1].upper() + sent[1:]


def _context(text, start, end, width=240):
    """The sentence that contains the match (bounded), with polite preambles removed."""
    bounds = [m.end() for m in re.finditer(r"(?<!\bRs)(?<!\bNo)[.!?]\s+|\n", text[:start])]
    s = max(bounds[-1] if bounds else 0, start - width)
    m = re.search(r"(?<!\bRs)(?<!\bNo)[.!?](\s|$)|\n", text[end:])
    e = min(end + m.start() if m else len(text), end + width)
    return tidy(text[s:e].strip(" ,.-:"))


def extract_dates(text: str, today: date | None = None):
    today = today or date.today()
    found, seen = [], set()
    for pat, kind in DATE_PATTERNS:
        for m in pat.finditer(text):
            try:
                if kind == "dmy":
                    d, mon, y = int(m.group(1)), MONTHS[m.group(2)[:3].lower()], _year(m.group(3), today)
                elif kind == "mdy":
                    mon, d, y = MONTHS[m.group(1)[:3].lower()], int(m.group(2)), _year(m.group(3), today)
                else:
                    d, mon, y = int(m.group(1)), int(m.group(2)), _year(m.group(3), today)
                dt = date(y, mon, d)
            except (ValueError, KeyError):
                continue
            if any(abs(m.start() - s) < 4 for s in seen):
                continue
            if re.search(r"\bdate[d]?\s*[:\-]?\s*$", text[max(0, m.start() - 12):m.start()], re.I):
                continue  # issue date in the letter header, not an event
            seen.add(m.start())
            ctx = _context(text, m.start(), m.end())
            before = text[max(0, m.start() - 45):m.start()]
            is_deadline = bool(DEADLINE_HINTS.search(before)) or bool(
                re.search(r"last date|final date|deadline|on or before", ctx, re.I))
            tm = TIME_RE.search(text[m.end():m.end() + 40])
            found.append({
                "date": dt.isoformat(),
                "time": tm.group(1).strip() if tm else None,
                "raw": m.group(0).strip(),
                "context": ctx[:160],
                "is_deadline": is_deadline,
                "days_left": (dt - today).days,
                "pos": m.start(),
            })
    found.sort(key=lambda x: x["pos"])
    uniq = {}
    for f in found:
        f.pop("pos")
        if f["date"] in uniq:
            uniq[f["date"]]["is_deadline"] |= f["is_deadline"]
            uniq[f["date"]]["time"] = uniq[f["date"]]["time"] or f["time"]
        else:
            uniq[f["date"]] = f
    return list(uniq.values())


def detect_audience(text: str):
    t = text.lower()
    sems = sorted(set(re.findall(r"\b(s[1-8])\b", t)), key=lambda s: int(s[1]))
    sems = [s.upper() for s in sems]
    for k, v in YEAR_TO_SEMS.items():
        if re.search(rf"\b{k}[\s-]?year", t):
            sems += [s for s in v if s not in sems]
    for m in re.finditer(r"\bs([1-8])\s*(?:&|and|,|to|-)\s*s?([1-8])\b", t):
        a, b = int(m.group(1)), int(m.group(2))
        for i in range(min(a, b), max(a, b) + 1) if "to" in m.group(0) or "-" in m.group(0) else (a, b):
            if f"S{i}" not in sems:
                sems.append(f"S{i}")
    branches = [b for b, rx in BRANCHES.items() if re.search(rx, t)]
    all_students = bool(re.search(r"\ball (the )?students\b|\ball branches\b|\ball semesters\b", t))
    if re.search(r"\ball branches\b", t) or (all_students and not sems):
        branches = []
    return {"semesters": sorted(set(sems), key=lambda s: int(s[1])), "branches": branches,
            "all_students": all_students}


def relevance(audience: dict, profile: dict | None):
    if not profile or not profile.get("semester"):
        return {"verdict": "maybe", "reason": "Set your semester & branch to personalise."}
    sem, br = profile.get("semester", "").upper(), profile.get("branch", "").upper()
    sems, brs = audience["semesters"], audience["branches"]
    sem_ok = not sems or sem in sems
    br_ok = not brs or br in brs
    if audience["all_students"] and not sems and not brs:
        return {"verdict": "yes", "reason": "Addressed to all students."}
    if sem_ok and br_ok:
        who = " ".join(filter(None, [", ".join(sems), ", ".join(brs)])) or "everyone"
        return {"verdict": "yes", "reason": f"Applies to {who} — that includes you ({sem} {br})."}
    return {"verdict": "no",
            "reason": f"Meant for {', '.join(sems + brs)} — you are {sem} {br}."}


def urgency(text: str, dates: list):
    t = text.lower()
    hits_hi = [w for w in URGENCY_WORDS["high"] if w in t]
    hits_md = [w for w in URGENCY_WORDS["medium"] if w in t]
    score = 3 * len(hits_hi) + len(hits_md)
    upcoming = [d["days_left"] for d in dates if d["days_left"] >= 0]
    if upcoming and min(upcoming) <= 3:
        score += 6
    elif upcoming and min(upcoming) <= 7:
        score += 3
    level = "high" if score >= 9 else "medium" if score >= 4 else "low"
    return {"level": level, "score": score, "signals": (hits_hi + hits_md)[:8]}


def action_sentences(text: str, limit=6):
    sents = re.split(r"(?<=[.!?])\s+|\n+", ABBR.sub(r"\1", text))
    out = []
    for s in sents:
        s = tidy(s.strip(" •-*\t"))
        if 15 < len(s) < 260 and ACTION_RE.search(s):
            out.append(s)
    return out[:limit]


def run(raw_text: str, profile: dict | None = None):
    t0 = datetime.now()
    text = clean(raw_text)
    dates = extract_dates(text)
    aud = detect_audience(text)
    venues = [v.strip() for v in VENUE_RE.findall(text)] + VENUE_AT_RE.findall(text)
    result = {
        "clean_text": text,
        "dates": dates,
        "deadlines": [d for d in dates if d["is_deadline"]],
        "times": list(dict.fromkeys(m.strip() for m in TIME_RE.findall(text)))[:6],
        "amounts": ["₹" + a for a in dict.fromkeys(AMOUNT_RE.findall(text))],
        "amount_details": [{"amount": "₹" + m.group(1), "context": _context(text, m.start(), m.end())}
                           for m in AMOUNT_RE.finditer(text)],
        "venues": list(dict.fromkeys(venues))[:4],
        "links": list(dict.fromkeys(URL_RE.findall(raw_text)))[:5],
        "emails": list(dict.fromkeys(EMAIL_RE.findall(raw_text)))[:3],
        "phones": list(dict.fromkeys(PHONE_RE.findall(raw_text)))[:3],
        "audience": aud,
        "relevance": relevance(aud, profile),
        "urgency": urgency(text, dates),
        "actions": action_sentences(text),
        "word_count": len(raw_text.split()),
        "removed_boilerplate_lines": len([l for l in raw_text.split("\n") if l.strip()]) - len(text.split("\n")),
    }
    result["ms"] = round((datetime.now() - t0).total_seconds() * 1000, 1)
    return result
