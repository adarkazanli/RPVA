"""Unit tests for entity extraction.

Tests LLM-based extraction of people, topics, and locations from notes.
"""

from unittest.mock import MagicMock, patch

import pytest

from ara.notes.extractor import EntityExtractor, ExtractedEntities


class TestEntityExtractor:
    """Test entity extraction from transcripts."""

    @pytest.fixture
    def mock_llm(self) -> MagicMock:
        """Create mock LLM that returns JSON extraction results."""
        llm = MagicMock()
        return llm

    @pytest.fixture
    def extractor(self, mock_llm: MagicMock) -> EntityExtractor:
        """Create extractor with mocked LLM."""
        return EntityExtractor(llm=mock_llm)

    def test_extract_person(self, extractor: EntityExtractor, mock_llm: MagicMock) -> None:
        """Test extraction of person names."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": ["John"], "topics": [], "locations": []}'
        )

        result = extractor.extract("I talked to John about the project")

        assert isinstance(result, ExtractedEntities)
        assert result.people == ["John"]
        assert result.topics == []
        assert result.locations == []

    def test_extract_multiple_people(self, extractor: EntityExtractor, mock_llm: MagicMock) -> None:
        """Test extraction of multiple people."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": ["Sarah", "John"], "topics": ["Q1 budget"], "locations": []}'
        )

        result = extractor.extract("Meeting with Sarah and John about Q1 budget")

        assert result.people == ["Sarah", "John"]
        assert result.topics == ["Q1 budget"]

    def test_extract_location(self, extractor: EntityExtractor, mock_llm: MagicMock) -> None:
        """Test extraction of location."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": [], "topics": [], "locations": ["Starbucks"]}'
        )

        result = extractor.extract("Coffee at Starbucks")

        assert result.locations == ["Starbucks"]

    def test_extract_all_entities(self, extractor: EntityExtractor, mock_llm: MagicMock) -> None:
        """Test extraction of all entity types."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": ["Sarah"], "topics": ["Q1 budget"], "locations": ["downtown office"]}'
        )

        result = extractor.extract(
            "Meeting with Sarah about Q1 budget at the downtown office"
        )

        assert result.people == ["Sarah"]
        assert result.topics == ["Q1 budget"]
        assert result.locations == ["downtown office"]

    def test_extract_empty_transcript(self, extractor: EntityExtractor, mock_llm: MagicMock) -> None:
        """Test extraction from empty transcript returns empty entities."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": [], "topics": [], "locations": []}'
        )

        result = extractor.extract("")

        assert result.people == []
        assert result.topics == []
        assert result.locations == []

    def test_extract_handles_malformed_json(
        self, extractor: EntityExtractor, mock_llm: MagicMock
    ) -> None:
        """Test extraction gracefully handles malformed JSON."""
        mock_llm.generate.return_value = MagicMock(text="not valid json")

        result = extractor.extract("Some transcript")

        # Should return empty entities on parse failure
        assert result.people == []
        assert result.topics == []
        assert result.locations == []

    def test_extract_handles_partial_json(
        self, extractor: EntityExtractor, mock_llm: MagicMock
    ) -> None:
        """Test extraction handles JSON with missing fields."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": ["John"]}'  # Missing topics and locations
        )

        result = extractor.extract("Talked to John")

        assert result.people == ["John"]
        assert result.topics == []  # Default to empty
        assert result.locations == []  # Default to empty

    def test_llm_called_with_prompt(
        self, extractor: EntityExtractor, mock_llm: MagicMock
    ) -> None:
        """Test LLM is called with extraction prompt."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": [], "topics": [], "locations": []}'
        )

        extractor.extract("Test transcript")

        mock_llm.generate.assert_called_once()
        call_args = mock_llm.generate.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "Test transcript" in prompt
        assert "people" in prompt.lower()
