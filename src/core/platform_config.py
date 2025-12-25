"""
Platform-specific response configuration for TruthShield
Optimized for different social media platforms
"""

from typing import Dict, List, Tuple, Optional
from pydantic import BaseModel


class PlatformSpec(BaseModel):
    """Platform-specific output specification"""
    name: str
    max_chars: int  # Soft limit, can vary
    char_range: Tuple[int, int]  # (min, max) flexible range
    sentences: Tuple[int, int]  # (min, max) sentence count
    required_sources: int
    source_format: str
    hashtag_count: Tuple[int, int]  # (min, max)
    emoji_density: str  # "none", "low", "medium", "high"
    tone_style: str  # Platform-native tone
    cta_style: Optional[str]  # Call-to-action style


# Platform specifications
PLATFORM_SPECS: Dict[str, PlatformSpec] = {
    "tiktok": PlatformSpec(
        name="TikTok",
        max_chars=450,
        char_range=(300, 500),  # Flexible range
        sentences=(4, 5),
        required_sources=3,
        source_format="Quellen: {sources}",  # "Quellen: A | B | C"
        hashtag_count=(3, 5),
        emoji_density="medium",
        tone_style="casual, engaging, Gen-Z friendly, hook-first",
        cta_style="Thoughts? 💭"
    ),

    "twitter": PlatformSpec(
        name="Twitter/X",
        max_chars=280,
        char_range=(200, 280),
        sentences=(2, 3),
        required_sources=2,
        source_format="📎 {sources}",
        hashtag_count=(1, 3),
        emoji_density="low",
        tone_style="concise, punchy, thread-aware",
        cta_style="Thread 🧵"
    ),

    "instagram": PlatformSpec(
        name="Instagram",
        max_chars=600,
        char_range=(400, 700),
        sentences=(4, 6),
        required_sources=3,
        source_format="Sources: {sources}",
        hashtag_count=(5, 10),
        emoji_density="high",
        tone_style="visual, story-driven, aesthetic",
        cta_style="Link in bio 👆"
    ),

    "linkedin": PlatformSpec(
        name="LinkedIn",
        max_chars=1000,
        char_range=(600, 1200),
        sentences=(5, 8),
        required_sources=3,
        source_format="References:\n{sources}",
        hashtag_count=(3, 5),
        emoji_density="low",
        tone_style="professional, thought-leadership, data-driven",
        cta_style="What's your take?"
    ),

    "youtube_comment": PlatformSpec(
        name="YouTube Comment",
        max_chars=500,
        char_range=(200, 500),
        sentences=(3, 5),
        required_sources=2,
        source_format="Sources: {sources}",
        hashtag_count=(0, 2),
        emoji_density="medium",
        tone_style="conversational, educational, community-focused",
        cta_style=None
    ),

    "reddit": PlatformSpec(
        name="Reddit",
        max_chars=800,
        char_range=(400, 1000),
        sentences=(4, 8),
        required_sources=3,
        source_format="**Sources:**\n{sources}",
        hashtag_count=(0, 0),  # Reddit doesn't use hashtags
        emoji_density="none",
        tone_style="detailed, skeptical, source-heavy, Redditor-native",
        cta_style=None
    ),
}


def get_platform_spec(platform: str) -> PlatformSpec:
    """Get platform specification, default to TikTok"""
    return PLATFORM_SPECS.get(platform.lower(), PLATFORM_SPECS["tiktok"])


def format_sources_for_platform(sources: List[str], platform: str) -> str:
    """Format source list according to platform spec"""
    spec = get_platform_spec(platform)

    # Limit to required number of sources
    limited_sources = sources[:spec.required_sources]

    if platform.lower() == "tiktok":
        # TikTok style: "Quellen: A | B | C"
        return spec.source_format.format(sources=" | ".join(limited_sources))

    elif platform.lower() == "reddit":
        # Reddit style: markdown list
        formatted = "\n".join([f"- {src}" for src in limited_sources])
        return spec.source_format.format(sources=formatted)

    elif platform.lower() == "linkedin":
        # LinkedIn style: numbered list
        formatted = "\n".join([f"{i+1}. {src}" for i, src in enumerate(limited_sources)])
        return spec.source_format.format(sources=formatted)

    else:
        # Default: comma-separated
        return spec.source_format.format(sources=", ".join(limited_sources))


def get_platform_prompt_modifier(platform: str, avatar: str) -> str:
    """Get platform-specific prompt instructions"""
    spec = get_platform_spec(platform)

    modifiers = {
        "tiktok": f"""
PLATFORM: TikTok
FORMAT REQUIREMENTS:
- Length: {spec.char_range[0]}-{spec.char_range[1]} characters (aim for ~{spec.max_chars})
- Sentences: {spec.sentences[0]}-{spec.sentences[1]}
- START with a HOOK (question, bold statement, or surprising fact)
- Include exactly {spec.required_sources} source references
- End sources with format: "Quellen: Source1 | Source2 | Source3"
- Emoji usage: {spec.emoji_density} (2-4 emojis max)
- Tone: {spec.tone_style}
- NO hashtags in the response (added separately)
- MUST be scroll-stopping and engagement-optimized
""",

        "twitter": f"""
PLATFORM: Twitter/X
FORMAT REQUIREMENTS:
- Length: STRICT {spec.max_chars} character limit
- Sentences: {spec.sentences[0]}-{spec.sentences[1]} max
- Be punchy and quotable
- Include {spec.required_sources} sources (shortened if needed)
- Tone: {spec.tone_style}
- Thread-ready (can be expanded)
""",

        "reddit": f"""
PLATFORM: Reddit
FORMAT REQUIREMENTS:
- Length: {spec.char_range[0]}-{spec.char_range[1]} characters
- Use markdown formatting where helpful
- Be detailed and evidence-based
- Redditors are skeptical - cite sources clearly
- NO emojis (Reddit culture)
- Include {spec.required_sources}+ sources with links
- Tone: {spec.tone_style}
""",

        "instagram": f"""
PLATFORM: Instagram
FORMAT REQUIREMENTS:
- Length: {spec.char_range[0]}-{spec.char_range[1]} characters
- Visual storytelling approach
- Emoji-rich ({spec.emoji_density} density)
- Include {spec.required_sources} sources
- Tone: {spec.tone_style}
""",

        "linkedin": f"""
PLATFORM: LinkedIn
FORMAT REQUIREMENTS:
- Length: {spec.char_range[0]}-{spec.char_range[1]} characters
- Professional tone with data points
- Thought-leadership positioning
- Include {spec.required_sources} credible sources
- Minimal emojis ({spec.emoji_density})
- Tone: {spec.tone_style}
"""
    }

    return modifiers.get(platform.lower(), modifiers["tiktok"])


# Avatar-Platform optimization matrix
AVATAR_PLATFORM_STYLES = {
    "GuardianAvatar": {
        "tiktok": "Witty fact-checker energy, 'let me break this down for you' vibes",
        "twitter": "Quick debunker, thread-master",
        "reddit": "Detailed fact-checker with receipts",
    },
    "MemeAvatar": {
        "tiktok": "Maximum chaos energy, 'bro what' reactions, chronically online",
        "twitter": "Ratio king, quote-tweet destroyer",
        "reddit": "Peak r/confidentlyincorrect material caller",
    },
    "ScienceAvatar": {
        "tiktok": "Science TikTok creator, 'actually...' energy, edu-tainment",
        "twitter": "Peer-review advocate, citation needed responder",
        "reddit": "r/science mod energy, asks for DOI",
    },
    "PolicyAvatar": {
        "tiktok": "Policy explainer, 'here's what the law actually says'",
        "twitter": "Official source linker, bureaucracy translator",
        "reddit": "Detailed policy breakdown with government sources",
    },
    "EuroShieldAvatar": {
        "tiktok": "EU fact-checker, Brussels insider vibes",
        "twitter": "Europa.eu link provider, treaty quoter",
        "reddit": "Detailed EU policy explainer with official sources",
    },
}


def get_avatar_platform_style(avatar: str, platform: str) -> str:
    """Get avatar-specific style for a platform"""
    avatar_styles = AVATAR_PLATFORM_STYLES.get(avatar, AVATAR_PLATFORM_STYLES["GuardianAvatar"])
    return avatar_styles.get(platform.lower(), avatar_styles.get("tiktok", ""))
