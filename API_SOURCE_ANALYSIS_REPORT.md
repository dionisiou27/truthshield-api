# TruthShield API - Quellen-Analyse Report
**Datum:** 2025-12-12
**Analysiert von:** Claude Code
**Projekt:** TruthShield API (Branch: sad-grothendieck)

---

## Executive Summary

### Hauptbefunde
1. **NUR 1 von 4 konfigurierten APIs ist aktiv** (Google Fact Check)
2. **Persona-spezifische Quellenauswahl FUNKTIONIERT**
3. **Statische Fallback-Quellen dominieren** (8/10 Quellen sind hardcodiert)
4. **Keine RSS-Feed Integration vorhanden**
5. **LLM Output-Diversität nicht getestet** (OpenAI API fehlt)

---

## 1. API-Verfügbarkeit

### Konfigurierte APIs

| API Service | Status | Ergebnis | Funktion |
|------------|--------|----------|----------|
| **OpenAI GPT-4** | ❌ NICHT KONFIGURIERT | 0 Calls | AI-Antworten, Fact-Checking |
| **Google Fact Check** | ✅ KONFIGURIERT | 0 Ergebnisse | Fact-Checker Suche |
| **NewsAPI** | ❌ NICHT KONFIGURIERT | 0 Calls | News-Kontext |
| **ClaimBuster** | ❌ NICHT KONFIGURIERT | 0 Calls | Claim-Scoring |
| **MediaWiki** | ✅ AKTIV | 4 Ergebnisse | Wikipedia/Wikidata |

### Test-Ergebnisse (Claim: "Ursula von der Leyen was not elected")

```
Total sources found: 10

API Calls:
  - Google Fact Check: Called = YES, Results = 0
  - NewsAPI: Called = NO (API key missing)
  - ClaimBuster: Called = NO (API key missing)
  - MediaWiki: Called = YES, Results = 4
  - Fallback sources added: 6
```

### Quellen-Breakdown

| # | Source | Type | Credibility | URL |
|---|--------|------|-------------|-----|
| 1 | EU-Austritt des Vereinigten Königreichs | MediaWiki | 0.82 | wikipedia.org |
| 2 | Europawahl 2024 | MediaWiki | 0.82 | wikipedia.org |
| 3 | Keir Starmer | MediaWiki | 0.82 | wikipedia.org |
| 4 | Wikiproject:Antispam/Qatar tracker | MediaWiki | 0.80 | meta.wikimedia.org |
| 5 | FactCheck.org | **Static Fallback** | 0.90 | factcheck.org |
| 6 | Snopes | **Static Fallback** | 0.85 | snopes.com |
| 7 | Mimikama | **Static Fallback** | 0.85 | mimikama.at |
| 8 | Correctiv | **Static Fallback** | 0.90 | correctiv.org |
| 9 | Wikipedia | **Static Fallback** | 0.80 | wikipedia.org |
| 10 | Europäisches Parlament wählt... | **Primary Source** | 0.97 | europarl.europa.eu |

**Analyse:** Nur 4 von 10 Quellen sind echte API-Ergebnisse. Die restlichen 6 sind statische Fallbacks.

---

## 2. Persona-spezifische Quellenauswahl

### Test-Ergebnisse

| Persona | Test Claim | Quellen | Persona-spezifisch? | Top Domains |
|---------|-----------|---------|---------------------|-------------|
| **ScienceAvatar** | COVID-19 vaccines | 17 | ✅ YES | science.org, fullfact.org, factcheck.org |
| **PolicyAvatar** | election results | 18 | ✅ YES | factcheck.org, politifact.com, usatoday.com |
| **EuroShieldAvatar** | EU policy | 15 | ✅ YES | europarl.europa.eu, ec.europa.eu |

### Befund: **Persona-Routing FUNKTIONIERT**

Die Funktion `_get_prioritized_sources()` (Zeile 854-943 in ai_engine.py) ist korrekt implementiert:

```python
bot_sources = {
    "ScienceAvatar": {
        "primary": [nature.com, science.org, who.int],
        "secondary": [factcheck, mimikama, correctiv]
    },
    "PolicyAvatar": {
        "primary": [factcheck.org, politifact.com, transparency.org, meta.wikimedia.org],
        "secondary": [mimikama, correctiv, snopes]
    },
    "EuroShieldAvatar": {
        "primary": [europa.eu, europarl.europa.eu, ec.europa.eu],
        "secondary": [factcheckeu, mimikama, correctiv]
    },
    ...
}
```

**Problem:** Diese Quellen sind STATISCH und werden IMMER hinzugefügt, unabhängig vom Claim-Inhalt.

---

## 3. Tatsächliche API-Nutzung

### Google Fact Check API

**Status:** Konfiguriert, aber **0 Ergebnisse**

**Code-Analyse (ai_engine.py:696-718):**
```python
if google_api_available:
    from src.services.google_factcheck import search_google_factchecks
    google_results = await search_google_factchecks(truncated_query, detected_lang)
    # Convert to Source objects
    for result in google_results[:5]:
        sources.append(source)
```

**Mögliche Gründe für 0 Ergebnisse:**
1. API Key ist ungültig/expired
2. Query nicht im Google Fact Check Index
3. Rate Limit überschritten
4. API Quota aufgebraucht

**Empfehlung:** API Key validieren mit direktem API Call

### MediaWiki API

**Status:** ✅ **FUNKTIONIERT**

4 Wikipedia/Wikidata Ergebnisse erfolgreich abgerufen.

**Code:** `src/services/wiki_api.py`
- Wikipedia: `fetch_wikipedia_pages()`
- Wikidata: `fetch_wikidata_entities()`
- Meta-Wiki: `fetch_meta_wiki_pages()`

### NewsAPI

**Status:** ❌ **NICHT AKTIV**

**Impact:** Keine aktuellen News-Artikel als Kontext.

**Code (ai_engine.py:720-742):**
```python
if news_api_available:
    from src.services.news_api import search_news_context
    news_results = await search_news_context(truncated_query, detected_lang)
    # Add max 3 news results
```

**Empfehlung:** NewsAPI Key in `.env` eintragen

### ClaimBuster API

**Status:** ❌ **NICHT AKTIV**

**Impact:** Kein automatisches Claim-Scoring.

**Code (ai_engine.py:769-796):**
```python
if claimbuster_api_available:
    from src.services.claimbuster_api import score_claim_worthiness
    claimbuster_score = await score_claim_worthiness(truncated_query)
    # Add ClaimBuster analysis as source
```

**Empfehlung:** ClaimBuster API Key in `.env` eintragen

---

## 4. Statische vs. Dynamische Quellen

### Aktuelle Verteilung (Beispiel: "Ursula von der Leyen")

| Typ | Anzahl | Prozent |
|-----|--------|---------|
| **MediaWiki API** | 4 | 40% |
| **Statische Fallbacks** | 6 | 60% |
| **Google Fact Check** | 0 | 0% |
| **NewsAPI** | 0 | 0% |
| **ClaimBuster** | 0 | 0% |

### Statische Fallback-Quellen (ai_engine.py:811-843)

```python
fallback_sources = [
    Source(url="https://www.factcheck.org", ...),
    Source(url="https://www.snopes.com", ...),
    Source(url="https://correctiv.org", ...)
]
```

**Problem:**
- Diese Quellen werden IMMER hinzugefügt, wenn < 3 Quellen gefunden wurden
- Keine tatsächliche Verifizierung des Claims auf diesen Websites
- Nur generische URLs, keine spezifischen Fact-Check Artikel

**Empfehlung:** Fallbacks nur als letzte Option, nicht bei jeder Query

---

## 5. Persona-Spezifische Primärquellen

### Konfigurierte Primärquellen pro Persona

#### ScienceAvatar
```python
"primary": [
    Source(url="https://www.nature.com/", credibility=0.95),
    Source(url="https://www.science.org/", credibility=0.95),
    Source(url="https://www.who.int/", credibility=0.95)
]
```
**Status:** ✅ Quellen vorhanden, aber NICHT dynamisch abgerufen

#### PolicyAvatar
```python
"primary": [
    Source(url="https://www.factcheck.org/", credibility=0.9),
    Source(url="https://www.politifact.com/", credibility=0.9),
    Source(url="https://www.transparency.org/", credibility=0.95),
    Source(url="https://meta.wikimedia.org/wiki/Public_policy", credibility=0.82)
]
```
**Status:** ✅ Quellen vorhanden, aber NICHT dynamisch abgerufen

#### EuroShieldAvatar
```python
"primary": [
    Source(url="https://europa.eu/", credibility=0.95),
    Source(url="https://www.europarl.europa.eu/", credibility=0.95),
    Source(url="https://ec.europa.eu/", credibility=0.95)
]
```
**Status:** ✅ Quellen vorhanden, aber NICHT dynamisch abgerufen

### **HAUPTPROBLEM:**
Diese "Primärquellen" sind **nur URLs ohne Inhalte**.
Es findet **KEIN Web Scraping** oder API-Abruf dieser Seiten statt.

---

## 6. LLM Output-Diversität

### OpenAI API Status
**Status:** ❌ **NICHT KONFIGURIERT**

**Impact:**
- Keine AI-generierte Fact-Check-Analyse
- Keine persona-spezifischen Antworten
- Fallback auf generische Templates

**Code (ai_engine.py:470-649):**
```python
async def _analyze_with_ai(self, text: str, company: str = "BMW") -> Dict:
    if not self.openai_client:
        return {"assessment": "limited", "reasoning": "No AI available"}
```

### Prompt-Analyse (ai_engine.py:1228-1258)

**Positiv:**
- Quellen werden in den Prompt eingefügt (Zeile 1214-1226)
- Instruction: "References specific facts from the verified sources"
- Instruction: "Uses concrete details (not generic statements)"

**Temperature-Setting:**
```python
temperature=0.7  # Line 1298
```
**Analyse:** 0.7 ist moderate Diversität. Für mehr Variation: 0.8-0.9

**Prompt-Struktur:**
```python
f"""
You are {company} {persona['emoji']}, {persona['style']}.

Voice: {persona['voice']}
Tone: {persona['tone']}
Humor Level: {humor_level}

VERIFIED SOURCES (use these facts in your response):
{sources_text}

{lang_instructions.get(language)}:
1. Matches your persona's humor level and style
2. Is engaging and appropriate for your audience
3. References specific facts from the verified sources above
4. Includes concrete details (not generic statements)
...
"""
```

**Befund:** Prompt ist gut strukturiert für dynamische Ausgaben.
**Problem:** Ohne OpenAI API Key nicht testbar.

---

## 7. RSS Feed Integration

**Status:** ❌ **NICHT VORHANDEN**

**Suche:** Kein Code für RSS-Feed-Parsing gefunden.

**Empfehlung:** RSS Feeds hinzufügen für:
- Fact-Checker Feeds (Correctiv, FactCheck.org, Snopes)
- EU Official Feeds (europa.eu/news)
- Science Journals (Nature, Science)

---

## 8. Kritische Befunde

### 🔴 Kritische Probleme

1. **Nur 1 von 4 APIs funktioniert**
   - Google Fact Check: 0 Ergebnisse trotz Konfiguration
   - NewsAPI: Nicht konfiguriert
   - ClaimBuster: Nicht konfiguriert
   - OpenAI: Nicht konfiguriert

2. **60% statische Fallback-Quellen**
   - Generische URLs ohne spezifische Artikel
   - Keine Verifizierung auf diesen Websites

3. **"Primärquellen" sind nur URLs**
   - ScienceAvatar → nature.com, science.org, who.int (nur Links!)
   - Kein tatsächliches Scraping oder API-Abruf
   - Keine spezifischen Artikel zum Claim

### ⚠️ Moderate Probleme

4. **Google Fact Check liefert 0 Ergebnisse**
   - Mögliche Ursachen: Invalid API Key, Rate Limit, Query nicht im Index
   - Muss validiert werden

5. **Keine RSS-Feed Integration**
   - Verpasste Chance für aktuelle Fact-Checks
   - Keine automatischen Updates von Fact-Checkern

6. **LLM Output nicht testbar**
   - OpenAI API fehlt
   - Diversität kann nicht validiert werden

### ✅ Was funktioniert

7. **Persona-spezifische Quellenauswahl funktioniert**
   - Korrekte Routing-Logik implementiert
   - Unterschiedliche Quellen pro Persona

8. **MediaWiki API funktioniert zuverlässig**
   - Wikipedia, Wikidata, Meta-Wiki erfolgreich abgerufen
   - 4 Ergebnisse pro Query

---

## 9. Empfehlungen

### Priority 1: API-Konfiguration (SOFORT)

1. **OpenAI API Key hinzufügen**
   ```bash
   OPENAI_API_KEY=sk-...
   ```
   **Impact:** AI-Antworten, Fact-Checking, Persona-Responses

2. **NewsAPI Key hinzufügen**
   ```bash
   NEWS_API_KEY=...
   ```
   **Impact:** Aktuelle News-Artikel als Kontext

3. **ClaimBuster API Key hinzufügen**
   ```bash
   CLAIMBUSTER_API_KEY=...
   ```
   **Impact:** Automatisches Claim-Scoring

4. **Google Fact Check API Key validieren**
   - Test mit direktem API Call
   - Quota überprüfen
   - Ggf. neuen Key erstellen

### Priority 2: Dynamische Quellenabfrage (HOCH)

5. **Web Scraping für Primärquellen implementieren**
   ```python
   # Statt nur URL zurückgeben:
   Source(url="https://www.nature.com/", ...)

   # Tatsächlich die Website abfragen:
   async def fetch_nature_articles(query):
       # Scrape nature.com/search?q={query}
       # Extrahiere relevante Artikel
       return articles
   ```

6. **Google Custom Search API integrieren**
   - Für ScienceAvatar: site:nature.com OR site:science.org
   - Für PolicyAvatar: site:factcheck.org OR site:politifact.com
   - Für EuroShieldAvatar: site:europa.eu OR site:europarl.europa.eu

7. **Fallback-Quellen nur als letzte Option**
   ```python
   # Aktuell: if len(sources) < 3
   # Besser: if len(sources) == 0
   ```

### Priority 3: RSS Feed Integration (MITTEL)

8. **RSS Feeds hinzufügen**
   ```python
   RSS_FEEDS = {
       "ScienceAvatar": [
           "https://www.nature.com/nature.rss",
           "https://www.science.org/rss/news_current.xml"
       ],
       "PolicyAvatar": [
           "https://www.factcheck.org/feed/",
           "https://www.politifact.com/rss/"
       ],
       "EuroShieldAvatar": [
           "https://europa.eu/newsroom/highlights/rss.xml"
       ]
   }
   ```

### Priority 4: LLM Output Diversität (MITTEL)

9. **Temperature erhöhen für mehr Variation**
   ```python
   # Aktuell: temperature=0.7
   # Empfehlung: temperature=0.8 oder 0.9
   ```

10. **System-Prompt variieren**
    ```python
    # Verschiedene Prompt-Templates pro Run
    # Zufällige Beispiele aus persona['examples']
    ```

### Priority 5: Monitoring & Logging (NIEDRIG)

11. **API Usage Tracking verbessern**
    ```python
    # Persistentes Logging:
    # - API Calls pro Tag
    # - Erfolgsrate pro API
    # - Durchschnittliche Ergebnisse
    ```

12. **Source Quality Metrics**
    ```python
    # Tracke für jede Quelle:
    # - Wie oft verwendet
    # - Credibility Score
    # - User Feedback
    ```

---

## 10. Implementierungsplan

### Phase 1: API-Aktivierung (1-2 Tage)

- [ ] OpenAI API Key in `.env` eintragen
- [ ] NewsAPI Key in `.env` eintragen
- [ ] ClaimBuster API Key in `.env` eintragen
- [ ] Google Fact Check API Key validieren
- [ ] Alle APIs testen mit `simple_api_test.py`

### Phase 2: Dynamische Quellen (3-5 Tage)

- [ ] Google Custom Search API integrieren
- [ ] Web Scraping für nature.com, science.org, who.int
- [ ] Web Scraping für factcheck.org, politifact.com
- [ ] Web Scraping für europa.eu, europarl.europa.eu
- [ ] Fallback-Logik anpassen (nur wenn 0 Quellen)

### Phase 3: RSS Feeds (2-3 Tage)

- [ ] RSS Parser implementieren (feedparser Library)
- [ ] RSS Feeds konfigurieren pro Persona
- [ ] Caching implementieren (Redis)
- [ ] Periodische Updates (Celery/Background Task)

### Phase 4: LLM Diversität (1-2 Tage)

- [ ] Temperature auf 0.8-0.9 erhöhen
- [ ] System-Prompt Variation implementieren
- [ ] Multiple LLM Calls mit verschiedenen Seeds
- [ ] A/B Testing für Output-Qualität

### Phase 5: Testing & Validation (2-3 Tage)

- [ ] Unit Tests für alle APIs
- [ ] Integration Tests für Persona-Routing
- [ ] Load Tests für API Rate Limits
- [ ] User Testing für Output-Qualität

---

## 11. Code-Beispiele für Fixes

### Fix 1: Dynamische Primärquellen (ScienceAvatar)

```python
async def _fetch_science_sources(self, query: str) -> List[Source]:
    """Fetch actual articles from scientific sources"""
    sources = []

    # Option 1: Google Custom Search API
    gcse_results = await self._google_custom_search(
        query,
        site_restrict="nature.com OR science.org OR who.int"
    )
    sources.extend(gcse_results)

    # Option 2: Direct scraping (if no API available)
    nature_articles = await self._scrape_nature(query)
    sources.extend(nature_articles)

    return sources[:5]  # Top 5 results

async def _scrape_nature(self, query: str) -> List[Source]:
    """Scrape nature.com search results"""
    url = f"https://www.nature.com/search?q={quote(query)}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        articles = []
        for article in soup.find_all('article', limit=5):
            title = article.find('h3').text
            link = article.find('a')['href']
            snippet = article.find('p').text[:200]

            articles.append(Source(
                url=f"https://www.nature.com{link}",
                title=title,
                snippet=snippet,
                credibility_score=0.95
            ))

        return articles
```

### Fix 2: RSS Feed Integration

```python
import feedparser
from datetime import datetime, timedelta

class RSSSourceManager:
    """Manage RSS feeds for fact-checking sources"""

    RSS_FEEDS = {
        "ScienceAvatar": [
            "https://www.nature.com/nature.rss",
            "https://www.science.org/rss/news_current.xml",
            "https://www.who.int/rss-feeds/news-english.xml"
        ],
        "PolicyAvatar": [
            "https://www.factcheck.org/feed/",
            "https://www.politifact.com/rss/",
            "https://www.transparency.org/rss"
        ],
        "EuroShieldAvatar": [
            "https://europa.eu/newsroom/highlights/rss.xml",
            "https://ec.europa.eu/commission/presscorner/rss/en"
        ]
    }

    async def fetch_rss_sources(self, persona: str, query: str) -> List[Source]:
        """Fetch recent articles from RSS feeds matching query"""
        feeds = self.RSS_FEEDS.get(persona, [])
        sources = []

        for feed_url in feeds:
            try:
                feed = feedparser.parse(feed_url)

                # Filter entries from last 30 days
                cutoff_date = datetime.now() - timedelta(days=30)

                for entry in feed.entries[:10]:  # Check last 10 entries
                    # Simple keyword matching
                    if self._matches_query(entry, query):
                        sources.append(Source(
                            url=entry.link,
                            title=entry.title,
                            snippet=entry.summary[:200],
                            credibility_score=0.85,
                            date_published=entry.published
                        ))

            except Exception as e:
                logger.error(f"RSS feed error: {e}")

        return sources[:5]  # Top 5 matches

    def _matches_query(self, entry, query: str) -> bool:
        """Check if RSS entry matches query keywords"""
        query_lower = query.lower()
        entry_text = (entry.title + " " + entry.get('summary', '')).lower()

        # Simple keyword matching (can be improved with NLP)
        keywords = query_lower.split()
        matches = sum(1 for kw in keywords if kw in entry_text)

        return matches >= len(keywords) * 0.5  # 50% keyword match
```

### Fix 3: Google Custom Search Integration

```python
async def _google_custom_search(self, query: str, site_restrict: str = None) -> List[Source]:
    """Use Google Custom Search API for domain-specific searches"""
    api_key = settings.google_api_key
    cx = settings.google_custom_search_cx  # Custom Search Engine ID

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": 5
    }

    if site_restrict:
        params["siteSearch"] = site_restrict
        params["siteSearchFilter"] = "i"  # Include only

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        data = response.json()

        sources = []
        for item in data.get('items', []):
            sources.append(Source(
                url=item['link'],
                title=item['title'],
                snippet=item.get('snippet', ''),
                credibility_score=0.8
            ))

        return sources
```

### Fix 4: Smarter Fallback Logic

```python
async def _search_sources(self, query: str, company: str = "GuardianAvatar") -> List[Source]:
    """Search with smart fallback strategy"""
    sources = []

    # Priority 1: Real API calls
    if google_api_available:
        google_results = await search_google_factchecks(query, lang)
        sources.extend(google_results[:5])

    if news_api_available:
        news_results = await search_news_context(query, lang)
        sources.extend(news_results[:3])

    # Priority 2: MediaWiki
    wiki_results = await search_mediawiki_sources(query, lang)
    sources.extend(wiki_results)

    # Priority 3: Persona-specific sources (DYNAMIC!)
    persona_sources = await self._fetch_persona_sources_dynamic(query, company)
    sources.extend(persona_sources)

    # Priority 4: RSS Feeds
    rss_sources = await self._fetch_rss_sources(query, company)
    sources.extend(rss_sources)

    # Priority 5: ClaimBuster
    if claimbuster_api_available:
        cb_results = await score_claim_worthiness(query)
        sources.extend(cb_results)

    # ONLY IF ZERO SOURCES: Use static fallbacks
    if len(sources) == 0:
        logger.warning("⚠️ No dynamic sources found, using static fallbacks")
        sources.extend(self._get_static_fallbacks(company)[:3])

    return sources[:10]  # Max 10 total sources
```

---

## 12. Zusammenfassung

### Ist-Zustand
- **1/4 APIs aktiv** (nur Google, aber 0 Ergebnisse)
- **60% statische Quellen** (nicht verifiziert)
- **Primärquellen sind nur URLs** (kein Content)
- **Persona-Routing funktioniert** (aber mit statischen Quellen)

### Soll-Zustand
- **4/4 APIs aktiv** (OpenAI, Google, NewsAPI, ClaimBuster)
- **100% dynamische Quellen** (echte API-Calls + Scraping)
- **Primärquellen mit Content** (spezifische Artikel)
- **Persona-Routing mit echten Quellen** (nature.com Artikel, nicht nur URL)

### Nächste Schritte
1. API Keys konfigurieren (.env)
2. Google Fact Check debuggen (warum 0 Ergebnisse?)
3. Web Scraping implementieren (nature.com, factcheck.org, europa.eu)
4. RSS Feeds integrieren
5. Fallback-Logik verbessern (nur bei 0 Quellen)

---

**Report Ende**
