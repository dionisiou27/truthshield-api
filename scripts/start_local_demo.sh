#!/usr/bin/env bash
#
# Start the TruthShield API locally and serve the demo page from the same
# origin (http://localhost:8000/demo).
#
# Serving the page from the API itself is deliberate: it removes both the
# CORS pre-flight and the mixed-content problem that appears when the
# GitHub Pages build (https://dionisiou27.github.io/truthshield-api/) calls
# http://localhost:8000 — Safari blocks that request outright.
#
# Usage:
#   ./scripts/start_local_demo.sh              # port 8000
#   PORT=8080 ./scripts/start_local_demo.sh    # custom port
#   FULL_DEPS=1 ./scripts/start_local_demo.sh  # install requirements.txt (incl. OCR/torch)
#
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PORT="${PORT:-8000}"
VENV_DIR="${VENV_DIR:-.venv}"
REQ_FILE="requirements-demo.txt"
[ "${FULL_DEPS:-0}" = "1" ] && REQ_FILE="requirements.txt"

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "❌ $PY not found. Install Python 3.11+." >&2; exit 1; }

# --- 1. Virtual environment ------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment in $VENV_DIR ..."
    "$PY" -m venv "$VENV_DIR"
fi
VENV_PY="$VENV_DIR/bin/python"
[ -x "$VENV_PY" ] || VENV_PY="$VENV_DIR/Scripts/python.exe"   # Git Bash on Windows

# --- 2. Dependencies (skipped when already importable) ---------------------
if ! "$VENV_PY" -c "import fastapi, uvicorn, openai, tweepy" >/dev/null 2>&1; then
    echo "📦 Installing dependencies from $REQ_FILE ..."
    "$VENV_PY" -m pip install --quiet --upgrade pip
    "$VENV_PY" -m pip install --quiet -r "$REQ_FILE"
else
    echo "✅ Dependencies already installed (skipping pip)."
fi

# --- 3. Configuration ------------------------------------------------------
if [ ! -f .env ]; then
    echo "⚠️  No .env found — copying .env.example (never commit .env)."
    cp .env.example .env
fi

# --- 4. Pre-flight: report which analysis backend will be used -------------
if [ -n "${OPENAI_BASE_URL:-}" ]; then
    echo "🔌 LLM endpoint: $OPENAI_BASE_URL (local / OpenAI-compatible)"
elif grep -qE '^OPENAI_API_KEY=.+' .env && ! grep -qE '^OPENAI_API_KEY=your_' .env; then
    echo "🔑 LLM endpoint: api.openai.com (requires internet access)"
else
    echo "⚠️  No usable OPENAI_API_KEY: the API will answer in DEGRADED mode"
    echo "    (sources are returned, but no verdict and no Guardian response)."
    echo "    Offline alternative — point the client at a local model:"
    echo "      export OPENAI_API_KEY=local OPENAI_BASE_URL=http://localhost:11434/v1"
    echo "      export OPENAI_MODEL_GENERATION=llama3.1 OPENAI_MODEL_CLASSIFICATION=llama3.1"
fi

# --- 5. Run ----------------------------------------------------------------
cat <<INFO

🛡️  TruthShield API starting
    Demo page : http://localhost:${PORT}/demo
    API docs  : http://localhost:${PORT}/docs
    Health    : http://localhost:${PORT}/health

INFO

exec "$VENV_PY" -m uvicorn src.api.main:app --host 0.0.0.0 --port "$PORT"
