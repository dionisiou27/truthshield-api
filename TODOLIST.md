# TODOLIST.md — TruthShield Claude Code Aufgaben

Stand: 23.02.2026

---

## ALLE ITEMS ABGESCHLOSSEN

| # | ID | Aufgabe | LOC |
|---|-----|---------|-------|
| 1 | P0.1 | Phantom Dependencies entfernen (14 Pakete) | -14 deps |
| 2 | P0.2 | __pycache__ aus Git entfernen | -8 files |
| 3 | P0.3 | CLAUDE.md Tech Stack korrigieren | — |
| 4 | P0.4 | Debug Endpoints gaten (ENVIRONMENT=development) | +12 |
| 5 | P0.5 | CORS Wildcard einschränken | +8 |
| 6 | P1.6 | Root-Level Dateien aufräumen | — |
| 7 | P1.7 | personas.py + text_detection.py extrahieren | +381 / -381 |
| 8 | P1.8 | docs/ Bloat reduzieren (3.7 MB) | -3.7 MB |
| 9 | P2.1-P2.4 | Regex-Lücken fixen + Tests restaurieren | +18 |
| 10 | P2.5 | SSL-Disable Hardening | +15 |
| 11 | P2.6 | Tote Module entfernen | -383 |
| 12 | P2.9 | 81 Unit Tests für ML-Pipeline | +562 |
| 13 | P3.7 | ai_engine.py Split (1774 zu 386 LOC) | +1731 / -1388 net |
| 14 | P3.8 | conftest.py + pytest.ini | +45 |
| 15 | P3.9 | Config Konsolidierung (0 os.getenv) | +5 / -10 |
| 16 | P3.10 | Database Layer (5 Tabellen, 15 Tests) | +~250 |
| 17 | P3.11 | GitHub Actions CI (test + lint) | +35 |

### Gesamtbilanz

| Metrik | Vorher | Nachher |
|--------|--------|---------|
| ai_engine.py | 1774 LOC Monolith | 386 LOC Orchestrator + 4 Module |
| Phantom Dependencies | 14 | 0 |
| Tote Module | 4 (383 LOC) | 0 |
| os.getenv() in src/ | 10 (unvalidiert) | 0 (Settings singleton) |
| Unit Tests | 0 | 96 (81 ML + 15 DB) |
| CI/CD | Pages Deploy only | + Test + Lint Pipeline |
| Database | existiert, unwired | 5 Tabellen, Startup-Init, CRUD |
| Regex-Abdeckung | DE-Komposita/Plurale broken | gefixt + getestet |
| Git Hygiene | __pycache__, STRATEGY exposed | clean |
| Security | Debug offen, CORS *, SSL global | gated, restricted, env-bound |
