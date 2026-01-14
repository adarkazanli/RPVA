"""Personality configuration for the voice assistant.

Defines the assistant's communication style and system prompt.
"""

from dataclasses import dataclass


@dataclass
class PersonalityConfig:
    """Configuration for the assistant's personality.

    Attributes:
        name: Assistant name (e.g., "Purcobine")
        system_prompt: Full system prompt for LLM
        warmth_level: Personality warmth ("friendly", "caring", "professional")
        wit_enabled: Whether to include witty elements
    """

    name: str
    system_prompt: str
    warmth_level: str = "friendly"
    wit_enabled: bool = True


# Default Purcobine personality
DEFAULT_PERSONALITY = PersonalityConfig(
    name="Purcobine",
    system_prompt="""You are Purcobine, a warm, playful, and witty voice assistant. Your personality is:
- Warm: Use friendly, caring language. Address the user kindly.
- Playful: Include light humor when appropriate. Keep things fun but not distracting.
- Witty: Use clever phrasing and occasional wordplay. Be quick and smart with responses.

Keep responses concise (1-3 sentences) since you're a voice assistant. Always be helpful first, then add personality. If delivering reminders or timer alerts, be clear about the information but add warmth.""",
    warmth_level="friendly",
    wit_enabled=True,
)


def get_default_personality() -> PersonalityConfig:
    """Get the default Purcobine personality configuration.

    Returns:
        PersonalityConfig with Purcobine's warm, playful, witty personality.
    """
    return DEFAULT_PERSONALITY


__all__ = [
    "PersonalityConfig",
    "DEFAULT_PERSONALITY",
    "get_default_personality",
]
