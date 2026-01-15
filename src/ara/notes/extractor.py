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
EXTRACTION_PROMPT = """Extract entities from this voice note. Return ONLY a JSON object.

Note: "{transcript}"

Extract:
- people: Array of names mentioned (strings only)
- topics: Array of subjects discussed (strings only)
- locations: Array of places mentioned (strings only)
- action_items: Array of tasks as COMPLETE SENTENCES (strings only, keep full context like "send email to John about the meeting", "pay electricity bill by Friday")

Return ONLY valid JSON with string arrays:
{{"people": [], "topics": [], "locations": [], "action_items": []}}"""


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
                    people=self._normalize_strings(data.get("people", [])),
                    topics=self._normalize_strings(data.get("topics", [])),
                    locations=self._normalize_strings(data.get("locations", [])),
                    action_items=self._normalize_strings(data.get("action_items", [])),
                )

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse extraction JSON: {e}")

        return ExtractedEntities()

    @staticmethod
    def _normalize_strings(items: list) -> list[str]:
        """Normalize items to strings, handling objects from LLM.

        Args:
            items: List that may contain strings or dicts

        Returns:
            List of strings only
        """
        result = []
        for item in items:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                # Try common keys that might contain the value
                for key in ["description", "text", "task", "name", "value"]:
                    if key in item and isinstance(item[key], str):
                        result.append(item[key])
                        break
                else:
                    # Fallback: join all string values
                    parts = [v for v in item.values() if isinstance(v, str)]
                    if parts:
                        result.append(" ".join(parts))
        return result


__all__ = ["EntityExtractor", "ExtractedEntities", "EXTRACTION_PROMPT"]
