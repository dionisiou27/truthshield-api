> **ALLE ITEMS ABGESCHLOSSEN** — 23.02.2026
>
> Sämtliche P0–P3 Bereinigungsaufgaben sind umgesetzt und validiert (96 Tests grün).
> Siehe CHANGELOG.md Eintrag vom 2026-02-23 für Details.

---

# TruthShield Repository — Bereinigungsliste

Stand: 23. Februar 2026 | Erstellt auf Basis eines vollständigen Code-Reviews

---

## P0 — Sofort (Glaubwürdigkeit bei Due Diligence)

### 1. `requirements.txt` — Phantom-Dependencies entfernen

**Problem:** 8 Libraries sind gelistet, aber nirgendwo in `src/` importiert. Ein Reviewer, der das prüft, verliert sofort Vertrauen.

**Nicht importiert, aber gelistet:**
- `langchain` — 0 Imports
- `transformers` — 0 Imports
- `torch` — 0 Imports
- `pandas` — 0 Imports
- `polars` — 0 Imports
- `pyarrow` — 0 Imports
- `scipy` — 0 Imports
- `statsmodels` — 0 Imports
- `scikit-learn` — 0 Imports
- `tweepy` — 0 Imports in `src/` (nur in Root-Level-Testdateien)
- `instagrapi` — 0 Imports

**Aktion:**
- Entferne alle nicht-importierten Libraries aus `requirements.txt`
- Erstelle optional `requirements-future.txt` oder kommentiere Ambitionen in der README
- `numpy` bleibt (wird in `ocr_service.py` verwendet)

### 2. `__pycache__` aus Git-History entfernen

**Problem:** 8 `.pyc`-Dateien sind committed. Signalisiert mangelnde Git-Hygiene.

**Betroffene Dateien:**
```
src/api/__pycache__/__init__.cpython-313.pyc
src/api/__pycache__/detection.cpython-313.pyc
src/api/__pycache__/main.cpython-313.pyc
src/api/__pycache__/monitoring.cpython-313.pyc
src/core/__pycache__/__init__.cpython-313.pyc
src/core/__pycache__/config.cpython-313.pyc
src/core/__pycache__/detection.cpython-313.pyc
src/services/__pycache__/social_monitor.cpython-313.pyc
```

**Aktion:**
```bash
git rm -r --cached src/api/__pycache__ src/core/__pycache__ src/services/__pycache__
```
`.gitignore` enthält bereits `__pycache__/` — also nur aus Tracking entfernen.

### 3. `CLAUDE.md` — Tech Stack korrigieren

**Problem:** Zeile 10 listet `Thompson Sampling Bandit, LangChain, Transformers, PyTorch` als aktiven Tech Stack. LangChain, Transformers und PyTorch werden nicht genutzt. Ein Gutachter, der `CLAUDE.md` liest und dann den Code prüft, sieht sofort die Diskrepanz.

**Aktion:** Tech Stack in `CLAUDE.md` auf tatsächlich genutzte Technologien reduzieren:
```
- AI/ML: OpenAI GPT-4-Turbo, Thompson Sampling Bandit (custom), BeautifulSoup4, EasyOCR
```

### 4. Debug-Endpoints entfernen

**Problem:** Zwei Debug-Endpoints sind in Production aktiv:
- `GET /debug/paths` — leakt Server-Dateipfade
- `GET /debug/env` — zeigt ob API-Keys existieren

**Aktion:** Hinter Environment-Check setzen oder komplett entfernen:
```python
if os.getenv("ENVIRONMENT") == "development":
    # Debug-Routen nur lokal
```

### 5. CORS-Wildcard entfernen

**Problem:** `allow_origins=["*"]` in `src/api/main.py:64`. Für einen Prototyp tolerabel, aber ein Security-Reviewer notiert das sofort. Widerspricht dem Compliance-Narrativ.

**Aktion:** Auf die bereits definierte `origins`-Liste umstellen (Zeile 50-59 ist korrekt, wird nur nicht genutzt).

---

## P1 — Diese Woche (Code-Qualität)

### 6. Root-Level-Datei-Chaos aufräumen

**Problem:** 7 lose Dateien im Root-Verzeichnis, die dort nicht hingehören:

| Datei | Aktion |
|-------|--------|
| `test_all_apis.py` | → `tests/` verschieben |
| `test_apis.py` | → `tests/` verschieben |
| `test_astroturfing.py` | → `tests/` verschieben |
| `test_astroturfing_simple.py` | → `tests/` verschieben |
| `test_charlie_kirk.py` | → `tests/` verschieben |
| `test_claimbuster_improved.py` | → `tests/` verschieben |
| `test_gdelt.py` | → `tests/` verschieben |
| `test_general_ev.py` | → `tests/` verschieben |
| `simple_api_test.py` | → `tests/` verschieben |
| `demo_script.py` | → `scripts/` oder `examples/` verschieben |
| `streamlit_app.py` | → `scripts/` verschieben oder entfernen |
| `create_strategy.ps1` | → `scripts/` verschieben oder entfernen |
| `main_backup.py` | Löschen (dafür gibt es Git) |
| `README.md.backup` | Löschen (dafür gibt es Git) |
| `API_SETUP.md` | → `docs/` verschieben |

### 7. `ai_engine.py` — Monolith aufbrechen

**Problem:** 2.131 Zeilen in einer Datei. Enthält mindestens 5 verschiedene Verantwortlichkeiten.

**Vorgeschlagene Aufteilung:**

| Neues Modul | Methoden | ~Zeilen |
|-------------|----------|---------|
| `src/core/persona_manager.py` | `company_personas`, Avatar-Definitionen, `TIKTOK_OUTPUT_RULES` | ~200 |
| `src/core/astroturfing.py` | `_detect_political_astroturfing()`, `_detect_astroturfing_indicators()` | ~200 |
| `src/core/contradiction.py` | `_detect_logical_contradictions()` | ~50 |
| `src/core/source_search.py` | `_search_sources()`, `_get_prioritized_sources()`, `_get_secondary_sources()` | ~400 |
| `src/core/verdict.py` | `_determine_verdict()`, `_apply_special_case_overrides()` | ~150 |
| `src/core/ai_engine.py` | Kern-Pipeline: `fact_check_claim()`, `_analyze_with_ai()`, `generate_brand_response()` | ~800 |

### 8. `docs/` — Bloat reduzieren

**Problem:** `docs/` ist 13 MB. Davon:
- `docs/images/` = 8.5 MB (PNG-Bilder, teilweise >1 MB)
- `docs/test.html` = 3.7 MB (was ist das?)
- `docs/index.html` = 63 KB

**Aktion:**
- `docs/test.html` prüfen — vermutlich löschen oder in `.gitignore`
- PNGs komprimieren (WebP oder optimierte PNGs → ~70% Reduktion)
- Erwäge, große Assets in Git LFS zu verschieben

---

## P2 — Nächste 2 Wochen (Technische Substanz)

### 9. Unit Tests für ML-Pipeline schreiben

**Problem:** Keine Unit Tests für die drei kritischsten Module:
- `ClaimRouter.classify_claim()` — keine Tests für Edge Cases
- `GuardianBandit.select_tone()` — keine Tests für kontextuelle Adjustierung
- `SourceRanker` — keine Tests für Ranking-Logik

**Minimum-Testset:**
```
tests/
├── unit/
│   ├── test_claim_router.py      # Jeder ClaimType mit 3+ Beispielen
│   ├── test_bandit.py            # Sampling, Update, State-Persistierung
│   ├── test_source_ranker.py     # Authority-Gewichtung, Topic-Boost
│   ├── test_coordinated.py       # Astro-Score mit bekannten Szenarien
│   └── test_negative_signals.py  # Reward Poisoning (aus bench/ extrahieren)
├── integration/
│   └── (bestehende Tests)
```

### 10. SSL-Disable-Pattern absichern

**Problem:** `DISABLE_SSL_VERIFY` deaktiviert SSL-Verifikation in 3 Dateien:
- `src/api/main.py`
- `src/services/rss_news.py`
- `src/services/who_api.py`

Auch wenn environment-gesteuert: In einer Security-Review ist das ein Finding.

**Aktion:** Logging hinzufügen wenn SSL disabled ist + Warnung in Startup-Log.

### 11. STRATEGY-Folder evaluieren

**Problem:** `STRATEGY/` enthält 66 KB an operativen Dokumenten (Influencer Research, Daily Operations Checklist, TikTok Policy Analysis). Frage: Gehört das in ein öffentliches Repository?

**Aktion:** Prüfen ob sensible Informationen enthalten sind. Falls ja → in privates Repo oder `.gitignore` verschieben.

---

## P3 — Mittelfristig (Architektur-Evolution)

### 12. Claim-Klassifikation über Regex hinaus

**Aktuell:** `classify_claim()` nutzt Regex-Pattern-Matching. Funktioniert für bekannte Muster, skaliert nicht für adversarial Content.

**Nächster Schritt:** Hybrid-Ansatz:
1. Regex als Fast-Path für bekannte Muster (behalten)
2. LLM-basierte Klassifikation als Fallback für unklare Claims
3. Mittelfristig: Fine-tuned Classifier (z.B. SetFit oder DistilBERT) für die 10 ClaimTypes

### 13. Datenbank-Layer implementieren

**Aktuell:** Bandit-State wird als JSON-File persistiert (`demo_data/ml/bandit_state.json`). Kein PostgreSQL trotz SQLAlchemy in Dependencies.

**Aktion:** Entweder PostgreSQL/SQLite tatsächlich anbinden oder SQLAlchemy/Alembic aus Requirements entfernen (→ siehe P0.1).

### 14. Environment-Management professionalisieren

**Aktuell:** Hardcoded Placeholder-Strings wie `"your_google_api_key_here"` in `ai_engine.py:1138-1140`.

**Aktion:** Pydantic Settings mit Validierung nutzen (ist bereits als Dependency vorhanden):
```python
class Settings(BaseSettings):
    openai_api_key: str
    google_api_key: Optional[str] = None
    # Validierung statt String-Vergleiche
```

---

## Zusammenfassung nach Aufwand

| Priorität | Items | Geschätzter Aufwand | Impact |
|-----------|-------|---------------------|--------|
| **P0** | 5 Items | 2-3 Stunden | Sofortige Glaubwürdigkeit bei technischer Review |
| **P1** | 3 Items | 1-2 Tage | Professionelle Code-Struktur |
| **P2** | 3 Items | 3-5 Tage | Technische Substanz und Testbarkeit |
| **P3** | 3 Items | 2-4 Wochen | Architektur-Evolution Richtung TRL 5 |

**Empfehlung:** P0 heute, P1 diese Woche. Der Rest nach Priorität und verfügbarer Zeit.
