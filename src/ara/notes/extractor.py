"""Entity extraction from voice transcripts.

Uses local LLM (Ollama) to extract people, topics, and locations.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntities:
    """Entities extracted from a note transcript."""

    people: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)


class LanguageModel(Protocol):
    """Protocol for language model inference."""

    def generate(self, prompt: str, **kwargs: Any) -> Any:
        """Generate response for prompt."""
        ...


# Prompt template for entity extraction
EXTRACTION_PROMPT = """Extract entities from this note. Return ONLY valid JSON with no additional text:
{{
  "people": ["name1", "name2"],
  "topics": ["topic1", "topic2"],
  "locations": ["location1"],
  "action_items": ["action1", "action2"]
}}

Rules:
- people: Names of specific people mentioned (e.g., "John", "Sarah", "Dr. Smith")
- topics: Main subjects or themes discussed (e.g., "Q1 budget", "project deadline")
- locations: Specific places mentioned (e.g., "Starbucks", "downtown office", "conference room")
- action_items: Tasks or actions the speaker needs to do, phrased as brief imperatives
  - Look for phrases like "I should...", "I need to...", "I will...", "I have to...", "need to..."
  - Convert to brief action format (e.g., "I should review the process" -> "review the process")
  - Only include clear actionable items, not observations or facts
- Return empty arrays [] if no entities found for a category
- Do NOT include generic references like "the team" unless it's a named team

Note: "{transcript}"

JSON:"""


class EntityExtractor:
    """Extracts people, topics, and locations from note transcripts.

    Uses local LLM for contextual extraction with structured JSON output.
    Performance target: <2 seconds per extraction.
    """

    def __init__(self, llm: LanguageModel) -> None:
        """Initialize extractor with language model.

        Args:
            llm: Language model for entity extraction (typically Ollama)
        """
        self._llm = llm

    def extract(self, transcript: str) -> ExtractedEntities:
        """Extract entities from transcript.

        Args:
            transcript: Raw voice transcript

        Returns:
            ExtractedEntities with people, topics, locations
        """
        if not transcript.strip():
            return ExtractedEntities()

        prompt = EXTRACTION_PROMPT.format(transcript=transcript)

        try:
            response = self._llm.generate(prompt, max_tokens=200, temperature=0.1)
            response_text = response.text if hasattr(response, "text") else str(response)

            return self._parse_response(response_text)

        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            return ExtractedEntities()

    def _parse_response(self, response_text: str) -> ExtractedEntities:
        """Parse LLM response into ExtractedEntities.

        Args:
            response_text: Raw LLM response (expected to be JSON)

        Returns:
            ExtractedEntities parsed from response
        """
        try:
            # Try to extract JSON from response (LLM might include extra text)
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                data = json.loads(json_str)

                return ExtractedEntities(
                    people=data.get("people", []),
                    topics=data.get("topics", []),
                    locations=data.get("locations", []),
                    action_items=data.get("action_items", []),
                )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse extraction JSON: {e}")

        return ExtractedEntities()


__all__ = ["EntityExtractor", "ExtractedEntities", "EXTRACTION_PROMPT"]
