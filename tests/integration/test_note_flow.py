"""Integration tests for note capture flow.

Tests end-to-end note capture with entity extraction.
"""

from unittest.mock import MagicMock

import pytest

from ara.notes import Category, EntityExtractor, Note, NoteService


class TestNoteCaptureFlow:
    """Test complete note capture workflow."""

    @pytest.fixture
    def mock_llm(self) -> MagicMock:
        """Create mock LLM for entity extraction."""
        llm = MagicMock()
        return llm

    @pytest.fixture
    def note_service(self, mock_llm: MagicMock) -> NoteService:
        """Create note service with mock LLM."""
        extractor = EntityExtractor(llm=mock_llm)
        return NoteService(extractor=extractor, user_id="test-user")

    def test_capture_note_with_person(
        self, note_service: NoteService, mock_llm: MagicMock
    ) -> None:
        """Test capturing a note extracts person correctly."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": ["John"], "topics": ["project deadline"], "locations": []}'
        )

        note = note_service.capture("I just talked to John about the project deadline")

        assert isinstance(note, Note)
        assert note.people == ["John"]
        assert note.topics == ["project deadline"]
        assert note.transcript == "I just talked to John about the project deadline"
        assert note.user_id == "test-user"

    def test_capture_note_with_meeting(
        self, note_service: NoteService, mock_llm: MagicMock
    ) -> None:
        """Test capturing meeting note extracts all entities."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": ["Sarah", "the marketing team"], "topics": ["campaign launch"], "locations": ["Starbucks"]}'
        )

        note = note_service.capture(
            "Meeting at Starbucks with Sarah and the marketing team about campaign launch"
        )

        assert note.people == ["Sarah", "the marketing team"]
        assert note.topics == ["campaign launch"]
        assert note.locations == ["Starbucks"]
        # Should be categorized as work (contains "meeting")
        assert note.category == Category.WORK

    def test_capture_note_auto_categorizes(
        self, note_service: NoteService, mock_llm: MagicMock
    ) -> None:
        """Test notes are auto-categorized based on content."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": [], "topics": ["weights"], "locations": ["gym"]}'
        )

        note = note_service.capture("Just finished my workout at the gym")

        assert note.category == Category.HEALTH

    def test_capture_note_with_activity(
        self, note_service: NoteService, mock_llm: MagicMock
    ) -> None:
        """Test note can be associated with an activity."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": [], "topics": ["code review"], "locations": []}'
        )

        note = note_service.capture(
            "Reviewed the PR for the new feature",
            activity_id="activity-123",
        )

        assert note.activity_id == "activity-123"

    def test_capture_empty_note(
        self, note_service: NoteService, mock_llm: MagicMock
    ) -> None:
        """Test capturing note with no extractable entities."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": [], "topics": [], "locations": []}'
        )

        note = note_service.capture("Something happened")

        assert note.people == []
        assert note.topics == []
        assert note.locations == []
        assert note.category == Category.UNCATEGORIZED

    def test_note_has_timestamp(
        self, note_service: NoteService, mock_llm: MagicMock
    ) -> None:
        """Test captured note has timestamp."""
        mock_llm.generate.return_value = MagicMock(
            text='{"people": [], "topics": [], "locations": []}'
        )

        note = note_service.capture("Test note")

        assert note.timestamp is not None


class TestNoteQueryFlow:
    """Test note query functionality."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        """Create mock repository."""
        repo = MagicMock()
        return repo

    @pytest.fixture
    def note_service_with_repo(self, mock_repository: MagicMock) -> NoteService:
        """Create note service with mock repository."""
        mock_llm = MagicMock()
        extractor = EntityExtractor(llm=mock_llm)
        return NoteService(
            extractor=extractor,
            repository=mock_repository,
            user_id="test-user",
        )

    def test_find_by_person(
        self, note_service_with_repo: NoteService, mock_repository: MagicMock
    ) -> None:
        """Test finding notes by person name."""
        mock_repository.find_by_person.return_value = [
            {
                "_id": "note-1",
                "transcript": "Talked to John about budget",
                "category": "work",
                "timestamp": None,
                "people": ["John"],
                "topics": ["budget"],
                "locations": [],
                "user_id": "test-user",
            }
        ]

        notes = note_service_with_repo.find_by_person("John")

        assert len(notes) == 1
        assert notes[0].people == ["John"]
        mock_repository.find_by_person.assert_called_once_with("John", 10)

    def test_find_by_person_no_results(
        self, note_service_with_repo: NoteService, mock_repository: MagicMock
    ) -> None:
        """Test finding notes when no matches."""
        mock_repository.find_by_person.return_value = []

        notes = note_service_with_repo.find_by_person("Unknown")

        assert notes == []
