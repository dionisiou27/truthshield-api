# 🔑 TruthShield API Setup Guide

## 📋 **Echte API-Integration implementiert!**

### ✅ **Verfügbare APIs (in `src/core/ai_engine.py`):**

#### **1. Google Fact Check API**
- **URL**: `https://factchecktools.googleapis.com/v1alpha1/claims:search`
- **Key**: `GOOGLE_API_KEY` in `.env`
- **Funktion**: Echte Fact-Check-Ergebnisse von Google
- **Credibility**: 0.9

#### **2. News API**
- **URL**: `https://newsapi.org/v2/everything`
- **Key**: `NEWS_API_KEY` in `.env`
- **Funktion**: Aktuelle Nachrichtenartikel
- **Credibility**: 0.75

#### **3. Bot-spezifische Primary-Quellen:**
- **EuroShieldBot**: europa.eu, europarl.europa.eu, ec.europa.eu
- **MemeBot**: Reddit Community Discussions
- **ScienceBot**: Nature, Science Magazine, WHO
- **PolicyBot**: FactCheck.org, PolitiFact, Transparency International
- **GuardianBot**: FactCheck.org, Snopes

### 🔧 **Setup-Anweisungen:**

#### **1. .env Datei erstellen:**
```bash
# TruthShield API Configuration
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
NEWS_API_KEY=your_news_api_key_here
```

#### **2. API-Keys besorgen:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Google Fact Check**: https://developers.google.com/fact-check/tools/api
- **News API**: https://newsapi.org/register

#### **3. Server starten:**
```bash
python -m uvicorn src.api.main:app --reload --port 8000
```

### 📊 **Aktuelle Implementierung:**

#### **Hierarchische Quellen-Priorisierung:**
1. **Primary Sources** (Bot-spezifisch)
2. **Secondary Sources** (Fallback)
3. **Real APIs** (Google Fact Check, News API)

#### **API-Status im Log:**
```
API Status - Google Fact Check: ✅/❌, NewsAPI: ✅/❌
```

### 🎯 **Nächste Schritte:**
1. **API-Keys** in `.env` eintragen
2. **Server neu starten**
3. **Demo testen** mit echten APIs
4. **Weitere APIs** hinzufügen (Snopes, Mimikama, etc.)

Die echten APIs sind jetzt implementiert! 🚀
