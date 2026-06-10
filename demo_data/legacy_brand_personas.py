"""
Legacy B2B Brand Personas (archived demo reference)
====================================================
These company personas date back to the early B2B brand-protection demo
(BMW / Vodafone / Bayer / Siemens). They are NOT part of the civil-society
Guardian avatar stack and are no longer wired into src/core. Kept here only as
a historical reference for demos and to document prior brand-voice experiments.

Do not import this from production code. The active personas live in
src/core/personas.py (GuardianAvatar, PolicyAvatar, MemeAvatar,
EuroShieldAvatar, ScienceAvatar).
"""

from typing import Dict, Any

LEGACY_BRAND_PERSONAS: Dict[str, Dict[str, Any]] = {
    "BMW": {
        "voice": "premium, technical, German engineering pride",
        "tone": "confident, fact-based, slightly humorous",
        "style": "engineering precision meets approachable communication",
        "emoji": "🚗"
    },
    "Vodafone": {
        "voice": "innovative, connected, tech-savvy",
        "tone": "friendly, educational, forward-thinking",
        "style": "modern communication technology expert",
        "emoji": "📱"
    },
    "Bayer": {
        "voice": "scientific, healthcare-focused, responsible",
        "tone": "professional, caring, evidence-based",
        "style": "trusted healthcare and science authority",
        "emoji": "💊"
    },
    "Siemens": {
        "voice": "industrial innovation, German precision",
        "tone": "technical expertise, reliable, progressive",
        "style": "engineering excellence with human touch",
        "emoji": "⚡"
    },
}
