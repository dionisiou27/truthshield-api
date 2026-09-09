# Running TruthShield locally (incl. fully offline)

A run-book for presenting TruthShield from a laptop — with a flaky connection,
a conference network, or no internet at all.

The GitHub Pages build (<https://dionisiou27.github.io/truthshield-api/>) is a
**static page**. It contains no backend: every analysis is an HTTP call to an
API that has to run somewhere. Presenting locally therefore means running that
API on the presentation machine and pointing the page at it.

---

## 1. Quick start

```bash
# macOS / Linux / Git-Bash
./scripts/start_local_demo.sh

# Windows / PowerShell
./scripts/start_local_demo.ps1
```

Then open **<http://localhost:8000/demo>**.

The script creates `.venv`, installs `requirements-demo.txt`, copies
`.env.example` to `.env` if needed, reports which analysis backend will be used,
and starts `uvicorn`. `PORT=8080 ./scripts/start_local_demo.sh` changes the port.

Manual equivalent:

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-demo.txt
cp .env.example .env
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

`requirements-demo.txt` deliberately omits `easyocr`, which pulls in `torch`
(~2 GB) and is only needed for the image/OCR endpoint. Use `requirements.txt`
(or `FULL_DEPS=1 ./scripts/start_local_demo.sh`) for the complete feature set.

---

## 2. Always present via `/demo`, not via GitHub Pages

The API serves the same page at `/demo`, so the browser request and the API
share one origin. Two failure modes disappear as a result:

1. **Mixed content.** A page delivered over `https://` (GitHub Pages) that calls
   `http://localhost:8000` is a mixed-content request. Chrome and Firefox treat
   `http://localhost` as a trustworthy origin and let it through; **Safari
   blocks it**. A demo that works on the rehearsal laptop and fails on the
   presentation laptop is usually this.
2. **CORS.** Cross-origin calls need the pre-flight to pass. `src/api/main.py`
   does allow-list `https://dionisiou27.github.io`, but same-origin requests
   skip the question entirely.

The demo page detects this automatically: when it is served from `localhost` /
`127.0.0.1`, it preselects that exact origin (including a non-default port) in
the *API Server* dropdown and runs the connection test on load. Opened via
`file://` it falls back to `http://localhost:8000`.

---

## 3. The three operating modes

The analysis verdict and the Guardian response are produced by an LLM. What the
demo can show therefore depends on what the LLM call can reach:

| Mode | Configuration | What the audience sees |
|------|---------------|------------------------|
| **A — Online** | `OPENAI_API_KEY` set, internet available | Full pipeline: verdict, confidence, Guardian response, live sources |
| **B — Offline, local model** | `OPENAI_BASE_URL` → local server (Ollama, LM Studio, vLLM) | Full pipeline; sources limited to the built-in institutional set |
| **C — No LLM** | no usable key / no reachable endpoint | `/health` reports `degraded`, the endpoint returns sources but **no verdict** and the placeholder "Response generation temporarily unavailable" |

Mode C is honest engineering (see `_build_degraded_fallback` in
`src/core/ai_engine.py`) but it is not a demo. **Do not present in mode C.**

### Mode B: offline with a local model

The OpenAI SDK reads `OPENAI_BASE_URL` from the environment, so any
OpenAI-compatible server works with **no code change**:

```bash
# once, WHILE STILL ONLINE:
ollama pull llama3.1

# at presentation time:
export OPENAI_API_KEY=local          # any non-empty string; not validated locally
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_MODEL_GENERATION=llama3.1
export OPENAI_MODEL_CLASSIFICATION=llama3.1
./scripts/start_local_demo.sh
```

PowerShell:

```powershell
$env:OPENAI_API_KEY="local"
$env:OPENAI_BASE_URL="http://localhost:11434/v1"
$env:OPENAI_MODEL_GENERATION="llama3.1"
$env:OPENAI_MODEL_CLASSIFICATION="llama3.1"
./scripts/start_local_demo.ps1
```

Verify before the talk:

```bash
curl http://localhost:8000/health
# -> {"status":"ok", ..., "subsystems":{"llm":"ok", ...}}
```

Notes and limits:

* `llm_model_status` stays `"unknown"` offline. Startup validation queries
  `api.openai.com/v1/models` (`src/core/llm_health.py`) and degrades to
  `"unknown"` when that host is unreachable — it does **not** block startup and
  does **not** disable the local model.
* The classification step requests `response_format={"type":"json_object"}`.
  Pick a local model that honours JSON mode; a model that emits prose around
  the JSON lands in the degraded path.
* Response quality is the local model's quality. For a scripted demo, rehearse
  the exact claims you intend to type.

### Offline behaviour of the remaining services

| Component | Offline |
|-----------|---------|
| Google Fact Check / Custom Search, News API, ClaimBuster, MediaWiki, CORE | fail per call, are caught, and simply contribute no sources |
| RSS freshness (`src/services/rss_freshness.py`) | no fresh coverage; territorial claims lose the freshness/corroboration boost |
| Built-in institutional sources (EU Parliament, Commission, FRA, Correctiv, Snopes, …) | still shown — the demo never looks empty |
| Image/OCR endpoint | unavailable unless `requirements.txt` was installed |

Front-end assets: Tailwind is vendored in `docs/vendor/` (see the README there)
and served by the API at `/vendor/...`, so the page renders offline. The Inter
web font is not vendored; offline the CSS stack falls back to `system-ui`,
which is a cosmetic difference only.

---

## 4. Pre-flight checklist (run it the day before, while online)

1. `pip install -r requirements-demo.txt` inside `.venv` — never install at the venue.
2. If using mode B: `ollama pull <model>` and one test question through Ollama itself.
3. Start the API, open `http://localhost:8000/demo`, confirm **✅ Connected**.
4. Run every claim you plan to show, exactly as you will type it, and check
   `"degraded": false` in *Show Raw JSON*.
5. Disable Wi-Fi and repeat step 4. Whatever survives that is your demo.
6. Keep a browser tab with a rehearsed result open as a fallback.

## 5. Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `❌ Offline` next to *Test* | API not running, or wrong port selected | Start the API; the dropdown must show the origin the page is served from |
| Page loads unstyled | vendored Tailwind missing | Restore `docs/vendor/tailwind.min.js` (see `docs/vendor/README.md`) |
| "Response generation temporarily unavailable" | mode C — no reachable LLM | Set `OPENAI_API_KEY`, or `OPENAI_BASE_URL` to a local model |
| `/health` shows `llm: misconfigured` | `OPENAI_MODEL_GENERATION` is not on the account | Set a model id the account actually has |
| Works in Chrome, not in Safari | mixed content from the https page to `http://localhost` | Present via `http://localhost:8000/demo` |
| `ModuleNotFoundError: tweepy` | dependencies incomplete | `pip install -r requirements-demo.txt` |
