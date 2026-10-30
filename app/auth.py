"""Minimal auth: PBKDF2-hashed passwords in users.json, random session tokens in sessions.json (HttpOnly cookie)."""
import hashlib
import hmac
import json
import secrets
import threading
import time
from pathlib import Path

DIR = Path(__file__).parent
USERS, SESSIONS = DIR / "users.json", DIR / "sessions.json"
COOKIE = "nl_session"
TTL = 7 * 24 * 3600
_lock = threading.Lock()


def _load(p):
    try:
        return json.loads(p.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(p, data):
    p.write_text(json.dumps(data, indent=1))


def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200_000).hex()


def register(name, email, password):
    email = email.strip().lower()
    with _lock:
        users = _load(USERS)
        if email in users:
            raise ValueError("An account with this email already exists.")
        salt = secrets.token_hex(16)
        users[email] = {"name": name.strip() or email.split("@")[0], "salt": salt, "hash": _hash(password, salt),
                        "created": time.time()}
        _save(USERS, users)
    return users[email]


def verify(email, password):
    u = _load(USERS).get(email.strip().lower())
    return u if u and hmac.compare_digest(u["hash"], _hash(password, u["salt"])) else None


def create_session(email):
    token = secrets.token_urlsafe(32)
    with _lock:
        s = {k: v for k, v in _load(SESSIONS).items() if v["exp"] > time.time()}
        s[token] = {"email": email.strip().lower(), "exp": time.time() + TTL}
        _save(SESSIONS, s)
    return token


def user_for(token):
    if not token:
        return None
    s = _load(SESSIONS).get(token)
    if not s or s["exp"] < time.time():
        return None
    u = _load(USERS).get(s["email"])
    return {"email": s["email"], "name": u["name"]} if u else None


def destroy(token):
    with _lock:
        s = _load(SESSIONS)
        s.pop(token, None)
        _save(SESSIONS, s)
