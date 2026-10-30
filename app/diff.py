"""Compare a new circular against a related earlier one: moved deadlines, new dates, changed amounts."""
import re

STOP = set("""the a an of to for and or is are be will on in at by from this that these those all students student
shall date dates dated has have been as it its their them which who per any other said hereby informed circular
notice following same also only than then into""".split())
MONTH_RE = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", re.I)
UPDATE_WORDS = re.compile(r"\b(revised|revision|extended|extension|modification|modified|postponed|preponed|"
                          r"rescheduled|corrigendum|addendum|amendment|in continuation|further to|update[d]?|"
                          r"changed|cancelled|reduced|increased)\b", re.I)


def _toks(s: str):
    s = MONTH_RE.sub(" ", s.lower())
    s = re.sub(r"[^a-z\s]", " ", s)
    return {w for w in s.split() if len(w) > 2 and w not in STOP}


def _sim(a: str, b: str):
    ta, tb = _toks(a), _toks(b)
    return len(ta & tb) / max(1, len(ta | tb))


def _pair(olds, news, okey, nkey, threshold=0.18):
    scored = sorted(((_sim(o[okey], n[nkey]), i, j) for i, o in enumerate(olds) for j, n in enumerate(news)),
                    reverse=True)
    used_o, used_n, pairs = set(), set(), []
    for sc, i, j in scored:
        if sc < threshold or i in used_o or j in used_n:
            continue
        used_o.add(i)
        used_n.add(j)
        pairs.append((olds[i], news[j]))
    return pairs, used_n


def compare(old_facts: dict, new_rules: dict):
    changes = []
    olds = old_facts.get("dates", [])
    news = new_rules["dates"]
    pairs, used_n = _pair(olds, news, "label", "context")
    for o, n in pairs:
        if o["date"] != n["date"]:
            changes.append({"kind": "moved", "label": n["context"], "old": o["date"], "new": n["date"],
                            "is_deadline": n["is_deadline"]})
    old_dates = {o["date"] for o in olds}
    for j, n in enumerate(news):
        if j not in used_n and n["date"] not in old_dates:
            changes.append({"kind": "added", "label": n["context"], "new": n["date"], "is_deadline": n["is_deadline"]})
    apairs, _ = _pair(old_facts.get("amounts", []), new_rules.get("amount_details", []), "context", "context", 0.15)
    for o, n in apairs:
        if o["amount"] != n["amount"]:
            changes.append({"kind": "amount", "label": n["context"], "old": o["amount"], "new": n["amount"]})
    return changes


def is_update(text: str, score: float):
    return score >= 0.35 or (score >= 0.12 and bool(UPDATE_WORDS.search(text)))
