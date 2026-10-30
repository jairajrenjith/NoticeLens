#!/usr/bin/env bash
# One-command start: creates venv if needed, then serves on http://localhost:8000
cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
