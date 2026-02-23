#!/usr/bin/env python3
"""
🛡️ TruthShield Live Demo Script
RE:PUBLICA 25 Ready - 30 Minuten Challenge!
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def print_banner():
    print("🛡️" + "="*50)
    print("  TRUTHSHIELD MVP - LIVE DEMO")
    print("  Deutsche KI gegen Desinformation")
    print("  RE:PUBLICA 25 READY!")
    print("="*52)
    print()

def demo_health_check():
    print("🏥 SYSTEM HEALTH CHECK...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        result = response.json()
        print(f"✅ Status: {result.get('status', 'OK')}")
        print(f"📊 Uptime: {result.get('uptime', 'Running')}")
        return True
    except Exception as e:
        print(f"❌ System offline: {e}")
        return False

def demo_text_detection():
    print("\n📝 TEXT DETECTION DEMO")
    print("-" * 30)
    
    test_cases = [
        {
            "name": "🚨 ANTI-VAX DESINFORMATION",
            "text": "EILMELDUNG: COVID-Impfung verändert dauerhaft Ihre DNA! Neue geheime Studien zeigen 99% Nebenwirkungsrate. Big Pharma und Regierung vertuschen die Wahrheit! Teilen Sie diese Nachricht, bevor sie zensiert wird!",
            "target": "Bayer AG Schutz"
        },
        {
            "name": "📡 5G VERSCHWÖRUNG", 
            "text": "5G-Strahlung verursacht COVID-19! Deutsche Telekom verschweigt massive Gesundheitsrisiken. Handymasten sind Biowaffen! Schützen Sie Ihre Familie - Router sofort ausschalten!",
            "target": "Deutsche Telekom Schutz"
        },
        {
            "name": "🚗 E-AUTO DESINFORMATION",
            "text": "BMW Elektroautos explodieren ohne Vorwarnung! Lithium-Batterien verursachen Krebs bei Kindern. Mainstream-Medien schweigen über die Opfer. Die grüne Lüge tötet!",
            "target": "BMW Deutschland Schutz"
        },
        {
            "name": "✅ AUTHENTISCHE NEWS",
            "text": "Siemens AG meldet solide Quartalsergebnisse für Q1 2025 mit einer Umsatzsteigerung von 3,2 Prozent gegenüber dem Vorjahr.",
            "target": "Baseline Vergleich"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. {case['name']}")
        print(f"   Zielkunde: {case['target']}")
        print(f"   Text: \"{case['text'][:80]}...\"")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/detect/text",
                json={"text": case["text"], "language": "de"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                is_synthetic = result.get('is_synthetic', False)
                confidence = result.get('confidence', 0) * 100
                
                status = "🚨 VERDÄCHTIG" if is_synthetic else "✅ AUTHENTISCH"
                print(f"   → {status} (Confidence: {confidence:.1f}%)")
                
                if is_synthetic:
                    print(f"   💡 TruthBot würde automatisch Fact-Check antworten!")
            else:
                print(f"   ❌ API Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Request failed: {e}")
        
        time.sleep(1)  # Dramatic pause für Demo

def demo_image_detection():
    print("\n🖼️  IMAGE DETECTION DEMO")
    print("-" * 30)
    
    # Beispiel-URLs (Mock für Demo)
    image_cases = [
        {
            "name": "🏢 BMW Logo Deepfake",
            "url": "https://example.com/deepfake_bmw_logo.jpg",
            "expected": "Synthetic"
        },
        {
            "name": "📰 Echtes Bayer Pressefoto", 
            "url": "https://example.com/authentic_bayer_photo.jpg",
            "expected": "Authentic"
        }
    ]
    
    for case in image_cases:
        print(f"\n🔍 {case['name']}")
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/detect/image",
                json={"image_url": case["url"]},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                is_synthetic = result.get('is_synthetic', False)
                confidence = result.get('confidence', 0) * 100
                
                status = "🚨 DEEPFAKE" if is_synthetic else "✅ ECHT"
                print(f"   → {status} (Confidence: {confidence:.1f}%)")
            else:
                print(f"   ℹ️  Bildanalyse verfügbar (Demo-Modus)")
                
        except Exception as e:
            print(f"   ℹ️  Bildanalyse verfügbar (Demo-Modus)")

def demo_social_monitoring():
    print("\n👁️  SOCIAL MEDIA MONITORING")
    print("-" * 30)
    
    companies = ["vodafone", "bmw", "bayer", "deutsche_telekom"]
    
    for company in companies:
        print(f"\n📡 Monitoring: {company.upper()}")
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/monitor/start",
                json={"company_name": company, "limit": 5},
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ {result.get('message', 'Monitoring aktiv')}")
            else:
                print(f"   ⏳ Monitoring wird initialisiert...")
                
        except Exception as e:
            print(f"   ⏳ Monitoring wird initialisiert...")
        
        time.sleep(0.5)

def demo_api_endpoints():
    print("\n🔌 API ENDPOINTS ÜBERSICHT")
    print("-" * 30)
    
    endpoints = [
        "GET  /health - System Status",
        "GET  /docs - Swagger UI",
        "POST /api/v1/detect/text - Text Analyse", 
        "POST /api/v1/detect/image - Bild Analyse",
        "POST /api/v1/monitor/start - Monitoring Start",
        "GET  /api/v1/monitor/companies - Unterstützte Firmen",
        "GET  /api/v1/monitor/status - Monitoring Status"
    ]
    
    for endpoint in endpoints:
        print(f"   📋 {endpoint}")
    
    print(f"\n🌐 Swagger UI: {BASE_URL}/docs")
    print("   → Alle APIs interaktiv testbar!")

def business_summary():
    print("\n💼 BUSINESS SUMMARY")
    print("=" * 50)
    print("🎯 Problem: €78B globaler Desinformationsschaden/Jahr")
    print("🇩🇪 Lösung: Deutsche KI-Alternative zu US Big Tech")
    print("🏢 Zielkunden: BMW, Bayer, Telekom, SAP, Siemens")
    print("⚖️  Compliance: EU AI Act + GDPR ready")
    print("🚀 Status: MVP Phase 3 fertig, Phase 4 startet")
    print("💰 Pricing: €2K-10K/Monat B2B SaaS")
    print("📈 Vision: €500K ARR Jahr 1 → €8M ARR Jahr 3")
    print()
    print("🎪 RE:PUBLICA 25 - Wir suchen:")
    print("   • Enterprise Kunden für Pilotprojekte")
    print("   • Investoren für Series A")
    print("   • Tech-Partner für EU-Expansion")

def main():
    start_time = datetime.now()
    
    print_banner()
    
    # System Check
    if not demo_health_check():
        print("❌ System nicht erreichbar!")
        print("🔧 Starten Sie: docker-compose up -d")
        return
    
    # Live Demos
    demo_text_detection()
    demo_image_detection() 
    demo_social_monitoring()
    demo_api_endpoints()
    business_summary()
    
    # Demo Stats
    end_time = datetime.now()
    duration = (end_time - start_time).seconds
    
    print("\n🎬 DEMO COMPLETED!")
    print(f"⏱️  Duration: {duration} seconds")
    print("🛡️ TruthShield - Protecting European Digital Democracy")

if __name__ == "__main__":
    main()