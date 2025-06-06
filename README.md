🛡️ UPDATED README.md FOR LIVE DEPLOYMENT
markdown# 🛡️ TruthShield - AI-Powered Influencer Protection

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-green.svg)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Live API](https://img.shields.io/badge/API-Live-success.svg)](https://truthshield-api.onrender.com)

## 🎯 Mission
Protecting influencers and brands from misinformation through AI-powered humor bots that make truth more viral than lies.

## 🌐 Live Demo & API

### 🚀 **API is LIVE!**
- **API Base URL**: https://truthshield-api.onrender.com
- **API Documentation**: https://truthshield-api.onrender.com/docs
- **Interactive Demo**: https://truthshield-demo.surge.sh *(Update with your Surge URL)*

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
🚀 What We're Building
TruthShield creates personalized AI characters that:

Detect misinformation about protected influencers in real-time
Respond with fact-based, humorous content in German & English 🇩🇪🇬🇧
Build engaged communities around truth
Make fact-checking entertaining, not preachy

🏗️ Architecture

Backend: FastAPI + Python 3.11 (Hosted on Render)
AI Engine: OpenAI GPT-3.5 with bilingual support
Frontend Demo: Static site on Surge
Deployment: TikTok-first, expanding to other platforms
Compliance: Full TikTok policy adherence with manual oversight

📊 Current Status

✅ LIVE API with real-time fact-checking
✅ Bilingual support (German/English)
✅ Working prototype with BMW, Vodafone, Bayer, Siemens
✅ TikTok compliance framework completed
✅ Weizenbaum Institute partnership in progress
🔄 First influencer protection bot in development

🔧 API Endpoints
Core Endpoints
MethodEndpointDescriptionPOST/api/v1/detect/fact-checkAnalyze content for misinformationPOST/api/v1/detect/quick-checkQuick fact-check without AI responseGET/api/v1/detect/companiesList supported companiesGET/api/v1/detect/statusDetection engine statusGET/healthHealth check endpointGET/docsInteractive API documentation
Example Request (Live API)
javascriptconst response = await fetch('https://truthshield-api.onrender.com/api/v1/detect/fact-check', {
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
console.log(result.ai_response); // AI-generated response in German/English
🌍 Bilingual Support
Our API now supports bilingual responses:

German 🇩🇪 - Primary language for DACH market
English 🇬🇧 - International expansion ready

Responses include both languages automatically:
json{
  "ai_response": {
    "response_text": "German response here..."
  },
  "details": {
    "ai_responses": {
      "de": "Als BMW stehen wir für Fakten...",
      "en": "At BMW, we stand for facts..."
    }
  }
}
🛠️ Local Development
Prerequisites

Python 3.11+
OpenAI API key
Git

Installation
bash# Clone repository
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
📈 Performance Metrics
Live API Stats

Response Time: ~2-5 seconds (including AI processing)
Uptime: 99.9% on Render free tier
Supported Companies: BMW, Vodafone, Bayer, Siemens
Languages: German & English

🤝 Partnerships

Academic: Weizenbaum Institute (Meeting: June 13, 2025)
Funding: Horizon Europe application (with Kyniska)
Target Influencers: Mai Thi Nguyen-Kim, Louisa Dellert, Raul Krauthausen

🚀 Roadmap
Phase 1: MVP ✅ (Current)

✅ Live API deployment
✅ Bilingual support
✅ Core fact-checking engine
✅ TikTok compliance framework
🔄 First influencer partnership

Phase 2: Scale (Q3 2025)

Multi-influencer support
Real-time TikTok monitoring
Advanced analytics dashboard
EU-based infrastructure

Phase 3: Expansion (Q4 2025)

Instagram, Twitter integration
Enterprise brand partnerships
€25K MRR target
Series A fundraising

🔒 Security & Compliance

GDPR Compliant: No personal data storage
API Rate Limiting: Prevents abuse
TikTok Compliant: Manual posting only
AI Transparency: Clear disclosure on all content

📞 Contact
Dionysios Andres - Founder & CEO
📧 contact@truthshield.eu
🌐 truthshield.eu
🔗 LinkedIn
📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
🙏 Acknowledgments

Weizenbaum Institute for research collaboration
Our early adopters and testers
The open-source community


<p align="center">
  <b>🚀 API Status: LIVE</b><br>
  <a href="https://truthshield-api.onrender.com/docs">Try it now!</a>
  <br><br>
  <i>"Making truth more entertaining than lies"</i> 🎭
  <br><br>
  <b>TruthShield - Where AI meets Accountability</b>
</p>
```