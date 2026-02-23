"""
Prompt construction helpers for Guardian Avatar response generation.
Extracted from ai_engine.py (P3.7).
"""
import random
from typing import List, Optional

from src.ml.guardian.claim_router import (
    TemporalMode, ClaimVolatility, ResponseMode,
    ResponseModeResult, EvidenceQuality,
)
from src.ml.learning.bandit import ToneVariant


def get_tone_instructions(tone_variant: ToneVariant, language: str) -> str:
    """
    Get dynamic tone instructions based on ML-selected variant.
    4 distinct tone buckets for real ML differentiation.
    """
    tone_configs = {
        ToneVariant.EMPATHIC: {
            "de": """
                VIBE: Verstehend, dann korrigierend. Du checkst die Angst/Sorge dahinter.
                HOOK: "Ich versteh die Sorge, aber..." / "Klingt scary, ist aber..."
                ENERGIE: Warm aber klar. Kein Mitleid, sondern Verständnis.
                BEISPIEL: "Ich versteh warum das beunruhigt. Aber hier sind die Fakten: [Zahl]. Checkt die Quelle."
                """,
            "en": """
                VIBE: Understanding first, then correcting. You get why people worry.
                HOOK: "I get why this sounds scary, but..." / "Makes sense to worry, but..."
                ENERGY: Warm but clear. Not pity, just understanding.
                EXAMPLE: "I get why this sounds scary. But here's what's actually true: [fact]. Check the source."
                """
        },
        ToneVariant.WITTY: {
            "de": """
                VIBE: Locker, selbstbewusst, leicht frech. Fakten mit Persönlichkeit.
                HOOK: "Nope." / "Ähm, ne." / "Plot twist:"
                ENERGIE: Entspannt-überlegen. Kein Stress, nur Klarheit.
                BEISPIEL: "Nope. Was wirklich passiert ist: [Fakt]. Easy zu checken."
                """,
            "en": """
                VIBE: Casual, confident, slightly cheeky. Facts with personality.
                HOOK: "Nope." / "Um, no." / "Plot twist:"
                ENERGY: Relaxed-confident. No stress, just clarity.
                EXAMPLE: "Nope. Here's what actually happened: [fact]. Easy to check."
                """
        },
        ToneVariant.FIRM: {
            "de": """
                VIBE: Direkt, keine Umwege. Fakt rein, fertig.
                HOOK: "Falsch." / "Das stimmt nicht." / "Die Daten zeigen:"
                ENERGIE: Sachlich-autoritär. Kein Raum für Diskussion.
                BEISPIEL: "Falsch. [Konkreter Fakt mit Zahl]. Quelle steht unten."
                """,
            "en": """
                VIBE: Direct, no detours. Fact in, done.
                HOOK: "False." / "That's not true." / "The data shows:"
                ENERGY: Matter-of-fact authoritative. No room for debate.
                EXAMPLE: "False. [Specific fact with number]. Source below."
                """
        },
        ToneVariant.SPICY: {
            "de": """
                VIBE: Bold, etwas provokant, aber faktisch korrekt. Weckt auf.
                HOOK: "Wilder Take." / "Reality Check:" / "Uff, ne."
                ENERGIE: Selbstbewusst-frech. Bricht die Bubble.
                BEISPIEL: "Wilder Take. Realität: [krasser Fakt]. Kannst du nachschauen."
                """,
            "en": """
                VIBE: Bold, slightly provocative, but factually correct. Wakes people up.
                HOOK: "Wild take." / "Reality check:" / "Oof, no."
                ENERGY: Confident-sassy. Breaks the bubble.
                EXAMPLE: "Wild take. Reality: [striking fact]. Look it up."
                """
        }
    }
    return tone_configs.get(tone_variant, tone_configs[ToneVariant.FIRM]).get(language, "en")


def get_opening_style(tone_variant: ToneVariant, language: str) -> str:
    """
    Get dynamic opening phrases based on ML-selected tone.
    Each bucket has distinct hooks - this is where ML learns what works.
    """
    openings = {
        ToneVariant.EMPATHIC: {
            "de": [
                "Ich versteh die Sorge.",
                "Klingt scary, aber:",
                "Verständlich, dass das nervt.",
                "Die Angst ist echt, aber:",
            ],
            "en": [
                "I get why this sounds scary.",
                "Makes sense to worry, but:",
                "I hear you, but here's the thing:",
                "The concern is real, but:",
            ]
        },
        ToneVariant.WITTY: {
            "de": [
                "Nope.",
                "Ähm, ne.",
                "Plot twist:",
                "Spoiler:",
                "Kurze Unterbrechung:",
            ],
            "en": [
                "Nope.",
                "Um, no.",
                "Plot twist:",
                "Spoiler alert:",
                "Quick interruption:",
            ]
        },
        ToneVariant.FIRM: {
            "de": [
                "Falsch.",
                "Das stimmt nicht.",
                "Die Daten zeigen:",
                "Fakt:",
                "Klarstellung:",
            ],
            "en": [
                "False.",
                "That's not true.",
                "The data shows:",
                "Fact:",
                "Correction:",
            ]
        },
        ToneVariant.SPICY: {
            "de": [
                "Wilder Take.",
                "Reality Check:",
                "Uff.",
                "Bold move, aber:",
                "Interessante Theorie.",
            ],
            "en": [
                "Wild take.",
                "Reality check:",
                "Oof.",
                "Bold claim, but:",
                "Interesting theory.",
            ]
        }
    }
    options = openings.get(tone_variant, openings[ToneVariant.FIRM]).get(language, "en")
    return random.choice(options) if isinstance(options, list) else options


def get_temporal_instructions(
    temporal_mode: TemporalMode,
    volatility: ClaimVolatility,
    is_territorial: bool,
    language: str,
) -> str:
    """
    Get time-aware response instructions based on claim volatility.
    Critical for TikTok where upload time != claim time.
    """
    if temporal_mode == TemporalMode.LIVE_REQUIRED:
        if is_territorial:
            return {
                "de": """
                    ⚡ ZEITKRITISCH: Territorial-Claim. Die Lage kann sich stündlich ändern.
                    - NIEMALS absolute Aussagen ("X kontrolliert Y")
                    - IMMER hedgen: "Nach aktuellen Berichten...", "Stand der letzten Meldungen..."
                    - Zeitliche Vorsicht: "Claims zur Gebietsrollen können sich schnell ändern"
                    """,
                "en": """
                    ⚡ TIME-CRITICAL: Territorial claim. Situation can change hourly.
                    - NEVER make absolute statements ("X controls Y")
                    - ALWAYS hedge: "According to latest reports...", "As of recent updates..."
                    - Temporal caution: "Claims about territorial control change rapidly"
                    """
            }.get(language, "en")
        else:
            return {
                "de": """
                    ⚡ LIVE-CHECK ERFORDERLICH: Volatile Situation.
                    - Vorsichtige Formulierung: "Nach aktuellen Informationen..."
                    - Keine absoluten Behauptungen
                    - Empfehlung: Aktuelle Quellen prüfen
                    """,
                "en": """
                    ⚡ LIVE CHECK REQUIRED: Volatile situation.
                    - Cautious phrasing: "Based on current information..."
                    - No absolute claims
                    - Recommend: Check latest sources
                    """
            }.get(language, "en")

    elif temporal_mode == TemporalMode.AMBIGUOUS:
        return {
            "de": """
                ❓ ZEITLICH UNKLAR: Gemischte Signale.
                - Vorsichtig bleiben
                - Keine definitiven Aussagen
                - Bei Unsicherheit hedgen
                """,
            "en": """
                ❓ TEMPORALLY UNCLEAR: Mixed signals.
                - Stay cautious
                - No definitive statements
                - Hedge when uncertain
                """
        }.get(language, "en")

    # ARCHIVE_OK - can be more direct
    return {
        "de": "✅ Stabile Faktenlage. Direkte Aussagen möglich.",
        "en": "✅ Stable factual basis. Direct statements OK."
    }.get(language, "en")


def get_response_mode_instructions(
    response_mode_result: Optional[ResponseModeResult],
    is_io: bool,
    io_indicators: List[str],
    language: str,
) -> str:
    """
    Get response framing instructions based on detected response mode.
    Now supports primary + secondary (overlay) modes.

    Routing Matrix:
    - CAUTIOUS > LIVE_SITUATION > IO_CONTEXT > DEBUNK
    - IO_CONTEXT can be overlay on LIVE_SITUATION
    """
    # Backwards compatibility: if no ResponseModeResult, use legacy logic
    if response_mode_result is None:
        return _get_legacy_response_mode_instructions(
            ResponseMode.DEBUNK, is_io, io_indicators, language
        )

    primary = response_mode_result.primary
    secondary = response_mode_result.secondary
    evidence_quality = response_mode_result.evidence_quality
    io_score = response_mode_result.io_score

    instructions_parts = []

    # === EVIDENCE QUALITY WARNING (always first) ===
    if evidence_quality == EvidenceQuality.WEAK:
        instructions_parts.append({
            "de": """
⚠️ SCHWACHE EVIDENZLAGE
- Du MUSST Hedging verwenden: "nach verfügbaren Berichten", "stand jetzt"
- KEINE definitiven Aussagen
- Anerkenne Unsicherheit explizit
                """,
            "en": """
⚠️ WEAK EVIDENCE BASE
- You MUST use hedging: "according to available reports", "as of now"
- NO definitive statements
- Acknowledge uncertainty explicitly
                """
        }.get(language, "en"))

    # === PRIMARY MODE INSTRUCTIONS ===
    if primary == ResponseMode.CAUTIOUS:
        instructions_parts.append({
            "de": """
❓ VORSICHT-MODUS: Unklare Faktenlage.
- Hedging ist PFLICHT
- Keine definitiven Aussagen möglich
- Auf weitere Quellen verweisen
- "Die Sachlage ist nicht eindeutig geklärt..."
                """,
            "en": """
❓ CAUTION MODE: Unclear factual basis.
- Hedging is MANDATORY
- No definitive statements possible
- Refer to additional sources
- "The facts are not definitively established..."
                """
        }.get(language, "en"))

    elif primary == ResponseMode.LIVE_SITUATION:
        instructions_parts.append({
            "de": """
⚡ LIVE-SITUATION: Fakten sind fluid.
- Keine absoluten Aussagen über territoriale Kontrolle
- "Nach aktuellen Berichten...", "Stand der letzten Meldungen..."
- Die Lage ändert sich schnell
- Datum/Zeit des letzten Updates nennen wenn möglich
                """,
            "en": """
⚡ LIVE SITUATION: Facts are fluid.
- No absolute statements about territorial control
- "According to latest reports...", "As of recent updates..."
- Situation changes rapidly
- Mention date/time of last update if possible
                """
        }.get(language, "en"))

    elif primary == ResponseMode.IO_CONTEXT:
        instructions_parts.append({
            "de": f"""
📢 INFORMATIONSOPERATION ERKANNT (Score: {io_score:.2f})
Indikatoren: {', '.join(io_indicators) if io_indicators else 'Narrativ-Muster'}

WICHTIG: Dies ist KEIN einfacher Faktencheck.
Der Claim ist Teil einer koordinierten Narrative.

Deine Antwort MUSS:
1. Das Narrativ benennen, nicht nur den Fakt widerlegen
2. "Diese Behauptung ist Teil einer laufenden Informationskampagne..."
3. Kontext geben: WARUM wird das jetzt verbreitet?
4. Nuanciert bleiben: Teilwahrheiten anerkennen, Framing entlarven

NICHT: "Das ist falsch."
SONDERN: "Diese Behauptung zirkuliert im Rahmen einer Kampagne..."
                """,
            "en": f"""
📢 INFORMATION OPERATION DETECTED (Score: {io_score:.2f})
Indicators: {', '.join(io_indicators) if io_indicators else 'Narrative patterns'}

IMPORTANT: This is NOT a simple fact-check.
The claim is part of a coordinated narrative campaign.

Your response MUST:
1. Name the narrative, don't just refute the fact
2. "This claim is part of an ongoing information campaign..."
3. Give context: WHY is this being spread now?
4. Stay nuanced: Acknowledge partial truths, expose framing

NOT: "This is false."
BUT: "This claim circulates as part of a campaign..."
                """
        }.get(language, "en"))

    elif primary == ResponseMode.DEBUNK:
        instructions_parts.append({
            "de": "✅ Standard Faktencheck. Klare Aussagen erlaubt.",
            "en": "✅ Standard fact-check. Clear statements allowed."
        }.get(language, "en"))

    # === SECONDARY (OVERLAY) MODE INSTRUCTIONS ===
    if secondary == ResponseMode.IO_CONTEXT:
        # This is the key case: LIVE_SITUATION + IO_CONTEXT
        instructions_parts.append({
            "de": f"""
📢 ZUSÄTZLICH: IO-OVERLAY (Score: {io_score:.2f})
Indikatoren: {', '.join(io_indicators) if io_indicators else 'Narrativ-Muster'}

Diese Live-Situation wird im Rahmen einer IO instrumentalisiert.
- Nenne das Narrativ ZUSÄTZLICH zu den Live-Fakten
- "Diese sich schnell ändernde Lage wird im Rahmen einer Kampagne instrumentalisiert..."
- Trenne: Was wir wissen vs. Wie es geframed wird
                """,
            "en": f"""
📢 ADDITIONALLY: IO OVERLAY (Score: {io_score:.2f})
Indicators: {', '.join(io_indicators) if io_indicators else 'Narrative patterns'}

This live situation is being instrumentalized as part of an IO.
- Name the narrative IN ADDITION to live facts
- "This rapidly changing situation is being instrumentalized as part of a campaign..."
- Separate: What we know vs. How it's being framed
                """
        }.get(language, "en"))

    return "\n".join(instructions_parts)


def _get_legacy_response_mode_instructions(
    response_mode: ResponseMode,
    is_io: bool,
    io_indicators: List[str],
    language: str,
) -> str:
    """Legacy method for backwards compatibility."""
    if response_mode == ResponseMode.IO_CONTEXT:
        return {
            "de": f"""
📢 INFORMATIONSOPERATION ERKANNT
Indikatoren: {', '.join(io_indicators) if io_indicators else 'Narrativ-Muster'}
Der Claim ist Teil einer koordinierten Narrative.
                """,
            "en": f"""
📢 INFORMATION OPERATION DETECTED
Indicators: {', '.join(io_indicators) if io_indicators else 'Narrative patterns'}
The claim is part of a coordinated narrative campaign.
                """
        }.get(language, "en")

    elif response_mode == ResponseMode.LIVE_SITUATION:
        return {
            "de": "⚡ LIVE-SITUATION: Fakten sind fluid. Keine absoluten Aussagen.",
            "en": "⚡ LIVE SITUATION: Facts are fluid. No absolute statements."
        }.get(language, "en")

    elif response_mode == ResponseMode.CAUTIOUS:
        return {
            "de": "❓ VORSICHT: Unklare Faktenlage. Hedging verwenden.",
            "en": "❓ CAUTION: Unclear factual basis. Use hedging."
        }.get(language, "en")

    return {
        "de": "✅ Standard Faktencheck. Klare Aussagen erlaubt.",
        "en": "✅ Standard fact-check. Clear statements allowed."
    }.get(language, "en")
