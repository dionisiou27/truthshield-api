# 🛡️ TruthShield - AI-Powered Democracy Protection

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Live API](https://img.shields.io/badge/API-Live-success.svg)](https://truthshield-api.onrender.com)

## 🎯 Mission
Building democracy's emotional immune system through Personality-Driven AI that transforms how society defends against misinformation. Our Character Intelligence Framework makes truth more engaging than lies through humor and behavioral science.

## 🌐 Live Demo & API

### 🚀 **API is LIVE!**
- **API Base URL**: https://truthshield-api.onrender.com
- **API Documentation**: https://truthshield-api.onrender.com/docs
- **Interactive Demo**: https://truthshield-demo.surge.sh

### Quick Test
```bash
# Test the live API
curl -X POST "https://truthshield-api.onrender.com/api/v1/detect/fact-check" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "BMW electric vehicles explode in winter",
    "company": "BMW",
    "language": "de",
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

- **Backend**: FastAPI + Python 3.11 (Hosted on Render)
- **AI Engine**: OpenAI GPT-3.5 with Character Intelligence Framework
- **Frontend Demo**: Static site on Surge
- **Deployment**: Multi-platform (TikTok, Twitter, Instagram)
- **Compliance**: Full social media policy adherence with manual oversight

## 📊 Current Status

- ✅ **LIVE API** with real-time fact-checking
- ✅ **Bilingual support** (German/English)
- ✅ **Character Intelligence Framework** with 8+ personas
- ✅ **Working prototypes** for BMW, Vodafone, Bayer, Siemens  
- ✅ **Academic discussions** with Tomorrow University of Applied Sciences
- 🔄 **First influencer protection** bot in development

## 🎭 Character Intelligence System

### Pre-configured Personas:
- **VodaBot** - Tech-savvy 5G conspiracy fighter
- **BMWBot** - Premium EV innovation defender  
- **BayerBot** - Gentle science communicator
- **GuardianBot** - Universal influencer protector
- **DemocracyDefender** - Political discourse guardian
- **MemeMaster** - Viral truth creator

## 🔬 Scientific Validation

Our approach is backed by peer-reviewed research:
- **20% reduction** in conspiracy belief (Science journal study)
- **2+ month duration** of belief change effects
- **Conversational AI** outperforms traditional fact-checking
- **Inoculation theory** prevents future misinformation susceptibility
- **Personality-driven engagement** increases intervention effectiveness

## 🔧 API Endpoints

### Core Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/detect/fact-check` | Analyze content for misinformation |
| POST | `/api/v1/detect/quick-check` | Quick fact-check without AI response |
| GET | `/api/v1/detect/companies` | List supported companies |
| GET | `/api/v1/detect/status` | Detection engine status |
| GET | `/health` | Health check endpoint |
| GET | `/docs` | Interactive API documentation |

### Example Request (Live API)
```javascript
const response = await fetch('https://truthshield-api.onrender.com/api/v1/detect/fact-check', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    text: "Vodafone 5G towers control minds",
    company: "Vodafone", 
    language: "de",
    generate_ai_response: true
  })
});

const result = await response.json();
console.log(result.ai_response); // AI-generated humorous response
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

### Live API Stats
- **Response Time**: ~2-5 seconds (including AI processing)
- **Uptime**: 99.9% on Render deployment
- **Supported Companies**: BMW, Vodafone, Bayer, Siemens
- **Languages**: German & English
- **Character Personas**: 8+ pre-configured

## 🤝 Market Validation & Opportunities

### Academic Interest
- **Tomorrow University of Applied Sciences** - Grant proposal discussions with Prof. Jonathan Costa

### Industry Validation
- **RHEINPFALZ Media Group** - Documented need: 3000+ weekly hate comments requiring moderation
- **Amadeu Antonio Stiftung** - Research data: 54% of Germans avoid political expression due to hate speech

### Funding Opportunities
- **Horizon Europe** Democracy-03 call (€3.5M available, deadline Sept 16, 2025)
- **Academic collaboration** discussions for joint grant applications

### Target Market
- German influencers and democratic voices under attack
- Media companies needing automated moderation solutions
- Political figures requiring reputation protection

## 🚀 Roadmap

### Phase 1: MVP ✅ (Current)
- ✅ Live API deployment
- ✅ Character Intelligence Framework  
- ✅ Bilingual support
- ✅ Academic discussions initiated
- 🔄 First influencer partnership negotiations

### Phase 2: Scale (Q3 2025)
- Multi-character deployment across platforms
- Real-time social media monitoring
- Advanced analytics dashboard
- EU Horizon funding application planned

### Phase 3: Expansion (Q4 2025)
- Instagram, Twitter, LinkedIn integration
- Enterprise brand partnerships
- €25K MRR target
- Series A fundraising

## 📊 Market Opportunity

### German Market Data
- **€60M annual market** for hate speech protection
- **54% of Germans** avoid political expression due to online hate
- **77% of hate comments** come from organized extremist campaigns
- **3000+ comments weekly** need moderation at major media companies

## 🔒 Security & Compliance

- **GDPR Compliant**: No personal data storage
- **API Rate Limiting**: Prevents abuse
- **Platform Compliant**: Manual posting protocols
- **AI Transparency**: Clear disclosure on all AI-generated content
- **Character Ethics**: Humor without harm principles

## 📞 Contact

**Dionysios Andres** - Founder & CEO  
📧 contact@truthshield.eu  
🌐 truthshield.eu  
📱 Testing: Personal TikTok deployment  

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Tomorrow University of Applied Sciences** for ongoing grant collaboration discussions
- **Prof. Jonathan Costa** for academic guidance and grant application expertise  
- **Our early adopters and testers**
- **The open-source community**
- **German civil society organizations** providing validation data

---

<p align="center">
  <b>🚀 API Status: LIVE</b><br>
  <a href="https://truthshield-api.onrender.com/docs">Try it now!</a>
  <br><br>
  <i>"Making truth more entertaining than lies"</i> 🎭
  <br><br>
  <b>TruthShield - Where AI meets Democracy</b>
</p>