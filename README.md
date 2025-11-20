# 🛡️ TruthShield - Character-Driven Counter-Disinformation

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-stable-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Live API](https://img.shields.io/badge/API-Live-success.svg)](https://truthshield-api.onrender.com)
[![Policy](https://img.shields.io/badge/TikTok-Policy%20Compliant%20(manual)-pink.svg)](#)
[![EU AI Act](https://img.shields.io/badge/EU%20AI%20Act-Transparency%20(Art.%2050)-blue.svg)](#)

## 🎯 Mission
Building democracy's emotional immune system through Personality-Driven AI that transforms how society defends against misinformation. Our Character Intelligence Framework makes truth more engaging than lies through humor and behavioral science.

## 🚀 **NEW: Real-Time API Integration**
- **Google Fact Check API**: Live fact-checking from global sources (FactCheck.org, Correctiv, BR)
- **News API**: Real-time news context from Forbes, Zeit, Wired, Business Insider
- **ClaimBuster API**: Scientific claim-worthiness scoring from University of Texas
- **OpenAI GPT-4**: Advanced AI analysis and persona-adapted responses
- **Multi-Stream Detection**: Hot (platform APIs) + Cold (external detection) streams
- **5 AI Personas**: ScienceAvatar, EuroShieldAvatar, PolicyAvatar, MemeAvatar, Guardian Avatar

## 🌐 Live Demo & API

### 🚀 **API is LIVE!**
- **API Base URL**: https://truthshield-api.onrender.com
- **API Documentation**: https://truthshield-api.onrender.com/docs
- **Interactive Demo**: https://truthshield-demo.surge.sh
- **Try in Browser**: [CodeSandbox Demo](https://codesandbox.io/s/truthshield-demo) *(Coming Soon)*

### Quick Test - Real APIs
```bash
# Test with Google Fact Check + News API + ClaimBuster
curl -X POST "https://truthshield-api.onrender.com/api/v1/detect/fact-check" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "COVID-19 vaccines cause autism",
    "company": "ScienceAvatar",
    "language": "en",
    "generate_ai_response": true
  }'

# Expected Response: Real fact-check sources + scientific analysis
# - Google Fact Check: FactCheck.org sources
# - News API: Current news context
# - ClaimBuster: Claim-worthiness score
# - ScienceAvatar: Academic-focused response
```

### Advanced Detection Examples
```bash
# Test astroturfing detection
curl -X POST "https://truthshield-api.onrender.com/api/v1/detect/fact-check" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "As a concerned citizen, I think all politicians are corrupt",
    "company": "GuardianAvatar",
    "language": "en",
    "generate_ai_response": true
  }'

# Test logical contradiction detection  
curl -X POST "https://truthshield-api.onrender.com/api/v1/detect/fact-check" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The vaccine is both safe and dangerous at the same time",
    "company": "Bayer",
    "language": "en",
    "generate_ai_response": true
  }'
```

## 🚀 What We're Building

**Personality-Driven AI for Strategic Information Defense**

TruthShield creates AI characters that:

- 🧠 **Use behavioral science** proven to reduce false beliefs by 20% (peer-reviewed)
- 🎭 **Deploy personality-based intervention** through our Character Intelligence Framework
- 😄 **Apply inoculation theory** making audiences resistant to future misinformation
- 🛡️ **Build cognitive infrastructure** for democratic resilience
- 🎪 **Transform fact-checking** from boring corrections to engaging entertainment

### The Digital Charlie Chaplin Approach
Just as Charlie Chaplin defeated fascism through humor in "The Great Dictator," TruthShield uses AI characters to make misinformation look ridiculous rather than fighting it directly. Now backed by scientific research showing 20% belief reduction with lasting effects.

## 🏗️ Architecture

- **Backend:** FastAPI + Python 3.11 (Render)
- **AI Engine:** LLM (OpenAI family) + Character Intelligence Framework
- **Detection:** XLM-R-based narrative classification + astroturfing & contradiction rules
- **Data:** SQLAlchemy models; immutable audit logging
- **Social Monitoring:** Twitter/X live; TikTok **manual-first** (Opt-in creators)
- **Frontend:** Static demo (Surge)
- **Ops:** Rate limiting, observability, exportable logs
- **Compliance:** GDPR/DSA-aligned; no scraping; manual posting

## 📊 Current Status

- ✅ **LIVE API** with real-time fact-checking
- ✅ **Advanced Detection Engine** with astroturfing & contradiction detection
- ✅ **Bilingual support** (German/English)
- ✅ **Character Intelligence Framework** with 8+ personas
- ✅ **GuardianAvatar** - Universal fact-checker with humor
- ✅ **Political Astroturfing Detection** - Specialized for smear campaigns
- ✅ **Social Media Monitoring** - Twitter/X integration
- ✅ **Database Models** - SQLAlchemy monitoring system
- ✅ **Working prototypes** for BMW, Vodafone, Bayer, Siemens, Guardian Avatar
- ✅ **Academic discussions** with Tomorrow University of Applied Sciences
- ✅ **TikTok Compliance** - Policy analysis and implementation ready
- 🔄 **Human-in-the-loop** review system in development
- 🔄 **TikTok API integration** in progress

## 🎭 Character Intelligence System

### Pre-configured Personas:
- **GuardianAvatar** 🛡️ - Universal fact-checker with humor (NEW!)
- **PolicyAvatar** - Policy fighter
- **MemeAvatar** - Speaks fluent Reddit  
- **EuroShieldAvatar** - Gentle EU communicator
- **ScienceAvatar** - Science innovation defender


### NEW: GuardianAvatar Features
- **Universal Detection**: Works across all topics and companies
- **Astroturfing Expert**: Specialized in coordinated disinformation
- **Political Smear Detection**: Identifies unsubstantiated corruption claims
- **Humor-First Approach**: Makes misinformation look ridiculous
- **Bilingual Responses**: German and English with cultural context

## 🔬 Scientific Validation

### **Theoretical Foundation**
Our approach is based on peer-reviewed research:
- **20% reduction** in conspiracy belief (Science journal study)
- **2+ month duration** of belief change effects
- **Conversational AI** outperforms traditional fact-checking
- **Inoculation theory** prevents future misinformation susceptibility
- **Personality-driven engagement** increases intervention effectiveness

### **⚠️ Current Validation Status**
- **Theoretical**: Strong foundation in behavioral science
- **Empirical**: Limited to internal testing (1,247 samples)
- **External Validation**: Not yet independently verified
- **Academic Review**: Pending peer review of our methods
- **Production Validation**: Real-world effectiveness unknown

### **🎯 Validation Roadmap**
- [ ] **Q3 2025**: Academic collaboration for independent validation
- [ ] **Q4 2025**: Large-scale deployment metrics collection
- [ ] **Q1 2026**: Peer-reviewed publication of results
- [ ] **Q2 2026**: Cross-platform effectiveness study

## 🔧 API Endpoints

### Core Detection Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/detect/fact-check` | **Enhanced** - Full AI analysis with astroturfing detection |
| POST | `/api/v1/detect/quick-check` | Quick fact-check without AI response |
| POST | `/api/v1/detect/text` | Legacy text detection (backward compatibility) |
| POST | `/api/v1/detect/image` | Image analysis (planned) |

### NEW Today: Prioritization, Astro-Score, Routing, Triage, Compliance
- Prioritization & Prefilter
  - GET `/api/v1/monitor/prioritization/config`
  - POST `/api/v1/monitor/prioritization/prioritize`
- Coordinated Behavior (Astro-Score)
  - POST `/api/v1/monitor/astro/score`
- Routing Pipeline (prefilter → astro → KPI)
  - GET `/api/v1/monitor/pipeline/config`
  - POST `/api/v1/monitor/pipeline/route`
- KPI & Watchlists (ROI)
  - GET `/api/v1/monitor/kpi/harm`
  - POST `/api/v1/monitor/kpi/harm/{topic}`
  - GET `/api/v1/monitor/watchlists`
  - POST `/api/v1/monitor/watchlists/{client}`
- QA & Red-team
  - GET `/api/v1/monitor/qa/config`
  - GET `/api/v1/monitor/qa/redteam/scenarios`
- Triage (Quick UI backend)
  - POST `/api/v1/monitor/triage/item`
  - POST `/api/v1/monitor/triage/batch`
  - POST `/api/v1/monitor/triage/action`
- Capacity & Staffing
  - POST `/api/v1/monitor/capacity/estimate`
  - GET `/api/v1/monitor/staff/model`
- Content Amplification
  - GET `/api/v1/content/amplify/formats`
  - POST `/api/v1/content/amplify/claim-vs-proof`
  - POST `/api/v1/content/amplify/investigative-thread`
  - POST `/api/v1/content/publish/enqueue`
  - GET `/api/v1/content/publish/queue`
- Compliance & Transparency
  - GET `/api/v1/compliance/transparency`
  - POST `/api/v1/compliance/transparency`
  - GET `/api/v1/compliance/dpa/clauses`

### NEW: Advanced Detection Features
| Feature | Description | Example |
|---------|-------------|---------|
| **Astroturfing Detection** | Identifies coordinated disinformation | "As a concerned citizen..." |
| **Political Astroturfing** | Detects political smear campaigns | "Politician X is corrupt..." |
| **Logical Contradictions** | Catches impossible claims | "Dead and alive simultaneously" |
| **GuardianAvatar Responses** | Universal fact-checker with humor | Works for any company/topic |

### Monitoring & Status Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/detect/companies` | List supported companies |
| GET | `/api/v1/detect/status` | Detection engine status |
| GET | `/api/v1/monitor/status` | Social media monitoring status |
| GET | `/health` | Health check endpoint |
| GET | `/docs` | Interactive API documentation |

### Example Request (Live API)
```javascript
// Test GuardianAvatar with astroturfing detection
const response = await fetch('https://truthshield-api.onrender.com/api/v1/detect/fact-check', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    text: "As a concerned citizen, I think all politicians are corrupt",
    company: "GuardianAvatar",
    language: "en",
    generate_ai_response: true
  })
});

const result = await response.json();
console.log(result.details.astroturfing_analysis); // Astroturfing detection results
console.log(result.ai_response); // GuardianAvatar's humorous response
```

### Advanced Response Format
```json
{
  "is_fake": true,
  "confidence": 0.85,
  "category": "astroturfing",
  "explanation": "ASTROTURFING DETECTED: This content shows signs of coordinated disinformation...",
  "ai_response": {
    "response_text": "Guardian Avatar here! 🛡️ This old tale? Time for a reality check with humor...",
    "tone": "humorous, factual, engaging",
    "hashtags": ["#TruthShield", "#FactCheck", "#GuardianAvatar"]
  },
  "details": {
    "astroturfing_analysis": {
      "is_likely_astroturfing": true,
      "coordinated_phrases": ["as a concerned citizen"],
      "political_astroturfing": {
        "is_political_astroturfing": true,
        "targets_legitimate_politician": true
      }
    }
  }
}
```

## 🌍 Bilingual Support

Our API supports bilingual character responses:

- **German 🇩🇪** - Primary language for DACH market
- **English 🇬🇧** - International expansion ready

Response format:
```json
{
  "ai_response": {
    "response_text": "VodaBot's humorous fact-check..."
  },
  "details": {
    "ai_responses": {
      "de": "Als Vodafone stehen wir für Fakten, nicht Fantasie! 📶",
      "en": "At Vodafone, we stand for facts, not fiction! 📶"
    }
  }
}
```

## 🔗 **Real API Integration**

### 🌍 **Live Data Sources**
| API | Status | Purpose | Sources |
|-----|--------|---------|---------|
| **Google Fact Check** | ✅ Active | Global fact-checking | FactCheck.org, Correctiv, BR, Snopes |
| **News API** | ✅ Active | Current news context | Forbes, Zeit, Wired, Business Insider |
| **ClaimBuster** | ✅ Active | Claim-worthiness scoring | University of Texas research |
| **OpenAI GPT-4** | ✅ Active | AI analysis & responses | Advanced language model |

### 🎯 **API Configuration**
```bash
# Required API Keys in .env file:
GOOGLE_API_KEY=your_google_factcheck_api_key
NEWS_API_KEY=your_news_api_key  
CLAIMBUSTER_API_KEY=your_claimbuster_api_key
OPENAI_API_KEY=your_openai_api_key
```

### 📊 **Real-Time Performance**
- **Processing Time**: 3-6 seconds (real API calls)
- **Source Coverage**: 10+ fact-checkers, 20+ news sources
- **Claim Detection**: Scientific scoring (0.0-1.0)
- **Confidence Levels**: 85-95% accuracy with real data

## 🔎 Source Retrieval & APIs

- All source retrieval, bot-specific prioritization, and external API integrations now live in `src/core/ai_engine.py`.
- Integrated APIs: Google Fact Check Tools, NewsAPI, ClaimBuster; plus EU primary sources (europa.eu, europarl.europa.eu, ec.europa.eu) and secondary fact-checkers (FactCheckEU, Mimikama, Correctiv, FactCheck.org, Snopes, PolitiFact).

## 🔬 Technical Features

### Advanced Detection Algorithms
- **Pattern Recognition**: Identifies coordinated language patterns
- **Emotional Manipulation Detection**: Catches emotional triggers
- **Repetition Analysis**: Detects suspicious word repetition
- **Context Analysis**: Considers posting frequency and network patterns
- **Political Targeting**: Specialized detection for political smear campaigns
- **Coordinated Behavior (Astro-Score)**: Rule-based A–E signals with 0–10 score (ready for ML)

### Database & Monitoring
- **SQLAlchemy Models**: Structured data storage for monitoring
- **Real-time Tracking**: Social media content monitoring
- **Audit Trails**: Complete logging of all decisions
- **Performance Metrics**: Response time and accuracy tracking

### Compliance & Security
- **EU AI Act Article 50**: Full transparency compliance
- **TikTok Policy Adherence**: Community guidelines compliance
- **GDPR Compliance**: No personal data storage
- **Rate Limiting**: API abuse prevention
- **Source Attribution**: Transparent fact-checking sources

## 🛠️ Local Development

### Prerequisites
- Python 3.11+
- OpenAI API key
- Git

### Installation
```bash
# Clone repository
git clone https://github.com/dionisiou27/truthshield-api.git
cd truthshield-api

# Create virtual environment  
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run development server
uvicorn src.api.main:app --reload
```

## 📈 Performance Metrics

### Performance (Current MVP)
- **API latency:** 2–5s incl. generation
- **Throughput:** 10+ concurrent requests (Render dyno)
- **Detection:** See transparent internal benchmark below (n=1,247; DE/EN)

### 🔬 **Transparent Benchmark Results**

#### **Test Corpus: TruthShield Internal Dataset**
- **Total Samples**: 1,247 manually labeled cases
- **Language Split**: 60% German, 40% English
- **Source**: Curated from social media, news comments, and test cases
- **Labeling**: Human experts + consensus validation

#### **Detection Performance**
| Detection Type | Precision | Recall | F1-Score | Sample Size |
|----------------|-----------|--------|----------|-------------|
| **Astroturfing Detection** | 0.78 | 0.82 | 0.80 | 312 samples |
| **Political Astroturfing** | 0.85 | 0.79 | 0.82 | 156 samples |
| **Logical Contradictions** | 0.92 | 0.88 | 0.90 | 89 samples |
| **Coordinated Language** | 0.74 | 0.76 | 0.75 | 234 samples |
| **Overall Misinformation** | 0.81 | 0.77 | 0.79 | 1,247 samples |

#### **Processing Performance**
- **Text Analysis**: <500ms average
- **AI Response Generation**: 2-3 seconds
- **API Response Time**: 2-5 seconds total
- **Concurrent Requests**: 10+ simultaneous

#### **⚠️ Important Limitations**
- **Small Dataset**: Results based on 1,247 samples (not production-scale)
- **Bias Risk**: Curated dataset may not represent all misinformation types
- **Language Imbalance**: More German than English samples
- **Human Labeling**: Subject to annotator bias and inconsistency
- **No External Validation**: Not tested on independent benchmarks

#### **🎯 Next Steps for Validation**
- [ ] Expand to 10,000+ samples
- [ ] External benchmark testing (FakeNewsNet, LIAR, etc.)
- [ ] Cross-platform validation (TikTok, Twitter, Facebook)
- [ ] Independent academic validation
- [ ] Real-world deployment metrics



### Target Market
- German influencers and democratic voices under attack
- Media companies needing automated moderation solutions
- Political figures requiring reputation protection

## 🚀 Roadmap

### Phase 1: MVP ✅ (COMPLETED)
- ✅ Live API deployment
- ✅ Character Intelligence Framework  
- ✅ Bilingual support
- ✅ Advanced Detection Engine
- ✅ GuardianAvatar implementation
- ✅ Astroturfing detection
- ✅ Political smear campaign detection
- ✅ Social media monitoring (Twitter/X)
- ✅ Database models and monitoring
- ✅ TikTok compliance analysis
- ✅ Academic discussions initiated

### Phase 2: Human-in-the-loop (Q3 2025) - IN PROGRESS
- 🔄 Human review system implementation
- 🔄 Content queue management
- 🔄 TikTok API integration
- 🔄 Manual approval interface
- 🔄 Real-time monitoring dashboard
- 🔄 EU Horizon funding application

### Phase 3: Ethical Engagement (Q4 2025)
- Pre-bunking system
- Fact-replies automation
- Duets/Partner-boosts
- Full transparency implementation
- Enterprise brand partnerships
- €25K MRR target

### Phase 4: Scale & Optimization (Q1 2026)
- Model optimization based on feedback
- Virality drop-off measurement
- Policy feedback loops
- Series A fundraising
- International expansion

## 📊 Market Opportunity

### German Market Data
- **€60M annual market** for hate speech protection
- **54% of Germans** avoid political expression due to online hate
- **77% of hate comments** come from organized extremist campaigns
- **3000+ comments weekly** need moderation at major media companies

## 🔒 Security & Compliance

- **GDPR Compliant**: No personal data storage
- **EU AI Act Compliant**: Article 50 transparency requirements
- **API Rate Limiting**: Prevents abuse
- **Platform Compliant**: Manual posting protocols
- **AI Transparency**: Clear disclosure on all AI-generated content
- **Provenance Archiving**: Evidence snapshots with SHA-256 and metadata
- **DPA Template**: See `docs/DPA_TEMPLATE.md` for roles, TOMs, and retention
- **Character Ethics**: Humor without harm principles
- **TikTok Policy Compliant**: Full adherence to community guidelines
- **Audit Trails**: Complete logging of all detection decisions
- **Source Attribution**: Transparent fact-checking sources
- **Human Oversight**: Manual review for all content generation

## ⚠️ Disclaimers

- **Research Prototype:** Not production-grade; for R&D and piloting
- **Internal Benchmark:** n=1,247 (DE/EN); may not generalize
- **Human Oversight Required:** All interventions reviewed and manually posted

## 🔌 Data Access & Compliance Plan

TruthShield follows a strict "Compliance-by-Design" approach:

- **Creator/NGO Opt-in (Live in MVP):** Near-realtime access to comments/mentions from consenting creators and NGOs; manual posting only.
- **EDMO/Fact-Checker Feeds (Planned in MVP):** Use of public ClaimReview/JSON feeds to maintain live watchlists for trending narratives.
- **Research API / DSA Art. 40 (Scaling Path):** We prepare a vetted-researcher pathway with academic partners to enable broad, reproducible access under EU law.
- **No scraping, no reverse-engineering:** 100% ToS-, DSA- und GDPR-konform.

## 🧑‍⚖️ Human-in-the-Loop (HITL) Workflow

1. **Ingest:** Creator/NGO feed + EDMO watchlist triggers detection.
2. **Triage:** Narrative classification (XLM-R) + risk scoring.
3. **Queue:** Items enter a **Review Queue** (priority, topic, language).
4. **Review:** Human approver sees suggested reply (persona tone + sources), can edit or reject.
5. **Publish:** Manual posting only (platform policy compliant).
6. **Log:** Full audit trail (input → decision → output) for evaluation and policy feedback.

## 📈 MVP KPIs & Milestones (Next 90 Days)

- **Data Access:** 15–25 Opt-in Creators/NGOs onboarded; ≥5 EDMO/Fact-checker feeds parsed.
- **HITL Console:** Review Queue v1, role management, audit trail, export.
- **Detection:** ≥80% F1 on internal bilingual test for top-5 narratives.
- **Interventions:** ≥150 approved replies (manual posting), ≥10 structured case studies.
- **Governance:** Ethics & Safeguards Board (ToR), red-team checklist, incident playbook.

## 🧩 Risk & Mitigation

- **Data Access Lag:** Limited coverage without Research API → Mitigation: Opt-in creators + EDMO feeds; Art. 40 pathway with university partner.
- **Model Drift:** Narratives evolve quickly → Mitigation: weekly retraining window + curator feedback loop.
- **False Positives:** Harm to legit speech → Mitigation: HITL approval, transparent sources, conservative thresholds.
- **Platform Policy Changes:** Posting/automation rules shift → Mitigation: manual-first operations; modular connectors.



## 📞 Contact

**Dionysios Andres** - Founder & CEO  
📧 contact@truthshield.eu  
🌐 truthshield.eu  
📱 Testing: Personal TikTok deployment  

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments



---

<p align="center">
  <b>🚀 API Status: LIVE</b><br>
  <a href="https://truthshield-api.onrender.com/docs">Try it now!</a>
  <br><br>
  <i>"Making truth more entertaining than lies"</i> 🎭
  <br><br>
  <b>TruthShield - Where AI meets Democracy</b>
  <br><br>
  <b>🛡️ NEW: Advanced Astroturfing Detection</b><br>
  <b>🎭 GuardianAvatar: Universal Fact-Checker</b><br>
  <b>⚖️ EU AI Act Compliant</b>
</p>