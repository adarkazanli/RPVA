"""Unit tests for MongoDB storage client.

Tests connection management, retry logic, and fallback behavior.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from ara.storage.models import (
    ActivityDTO,
    ActivityStatus,
    EventDTO,
    EventType,
    InteractionDTO,
)


class TestInteractionDTO:
    """Tests for InteractionDTO serialization."""

    def test_to_dict(self) -> None:
        """Test InteractionDTO converts to dict correctly."""
        dto = InteractionDTO(
            session_id="session-123",
            timestamp=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
            device_id="device-1",
            transcript="what time is it",
            transcript_confidence=0.95,
            intent_type="time_query",
            intent_confidence=0.9,
            response_text="It is 10:30 AM",
            response_source="local",
            latency_ms={"total": 150, "stt": 50, "llm": 100},
            entities={"query_type": "time"},
        )

        result = dto.to_dict()

        assert result["session_id"] == "session-123"
        assert result["device_id"] == "device-1"
        assert result["input"]["transcript"] == "what time is it"
        assert result["input"]["confidence"] == 0.95
        assert result["intent"]["type"] == "time_query"
        assert result["intent"]["confidence"] == 0.9
        assert result["intent"]["entities"] == {"query_type": "time"}
        assert result["response"]["text"] == "It is 10:30 AM"
        assert result["response"]["source"] == "local"
        assert result["latency_ms"]["total"] == 150

    def test_from_dict(self) -> None:
        """Test InteractionDTO creates from dict correctly."""
        data = {
            "_id": "abc123",
            "session_id": "session-456",
            "timestamp": datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC),
            "device_id": "device-2",
            "input": {
                "transcript": "set a timer",
                "confidence": 0.88,
                "audio_duration_ms": 1500,
            },
            "intent": {
                "type": "timer_set",
                "confidence": 0.92,
                "entities": {"duration": "5 minutes"},
            },
            "response": {
                "text": "Timer set for 5 minutes",
                "source": "local",
            },
            "latency_ms": {"total": 200},
            "events_extracted": ["event-1"],
        }

        dto = InteractionDTO.from_dict(data)

        assert dto.id == "abc123"
        assert dto.session_id == "session-456"
        assert dto.transcript == "set a timer"
        assert dto.transcript_confidence == 0.88
        assert dto.audio_duration_ms == 1500
        assert dto.intent_type == "timer_set"
        assert dto.entities == {"duration": "5 minutes"}
        assert dto.events_extracted == ["event-1"]


class TestEventDTO:
    """Tests for EventDTO serialization."""

    def test_to_dict(self) -> None:
        """Test EventDTO converts to dict correctly."""
        dto = EventDTO(
            interaction_id="interaction-123",
            timestamp=datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC),
            event_type=EventType.ACTIVITY_START,
            context="gym",
            source_text="I'm going to the gym",
            extraction_confidence=0.9,
            entities={"activity": "gym"},
        )

        result = dto.to_dict()

        assert result["interaction_id"] == "interaction-123"
        assert result["type"] == "activity_start"
        assert result["context"] == "gym"
        assert result["entities"] == {"activity": "gym"}
        assert result["metadata"]["source_text"] == "I'm going to the gym"
        assert result["metadata"]["extraction_confidence"] == 0.9

    def test_from_dict(self) -> None:
        """Test EventDTO creates from dict correctly."""
        data = {
            "_id": "event-abc",
            "interaction_id": "interaction-456",
            "timestamp": datetime(2024, 1, 15, 15, 0, 0, tzinfo=UTC),
            "type": "activity_end",
            "context": "gym",
            "entities": {"duration_hint": "1 hour"},
            "linked_event_id": "event-xyz",
            "activity_id": "activity-123",
            "metadata": {
                "source_text": "finished at the gym",
                "extraction_confidence": 0.85,
            },
        }

        dto = EventDTO.from_dict(data)

        assert dto.id == "event-abc"
        assert dto.event_type == EventType.ACTIVITY_END
        assert dto.context == "gym"
        assert dto.linked_event_id == "event-xyz"
        assert dto.activity_id == "activity-123"


class TestActivityDTO:
    """Tests for ActivityDTO serialization."""

    def test_to_dict(self) -> None:
        """Test ActivityDTO converts to dict correctly."""
        dto = ActivityDTO(
            name="gym session",
            status=ActivityStatus.COMPLETED,
            start_event_id="event-1",
            start_time=datetime(2024, 1, 15, 14, 0, 0, tzinfo=UTC),
            start_text="going to gym",
            pairing_score=0.95,
            end_event_id="event-2",
            end_time=datetime(2024, 1, 15, 15, 30, 0, tzinfo=UTC),
            duration_ms=5400000,
            end_text="back from gym",
        )

        result = dto.to_dict()

        assert result["name"] == "gym session"
        assert result["status"] == "completed"
        assert result["start_event_id"] == "event-1"
        assert result["end_event_id"] == "event-2"
        assert result["duration_ms"] == 5400000
        assert result["context"]["start_text"] == "going to gym"
        assert result["context"]["end_text"] == "back from gym"

    def test_from_dict_in_progress(self) -> None:
        """Test ActivityDTO creates in-progress activity from dict."""
        data = {
            "_id": "activity-abc",
            "name": "shower",
            "status": "in_progress",
            "start_event_id": "event-1",
            "start_time": datetime(2024, 1, 15, 8, 0, 0, tzinfo=UTC),
            "context": {"start_text": "taking a shower"},
            "pairing_score": 0.8,
        }

        dto = ActivityDTO.from_dict(data)

        assert dto.id == "activity-abc"
        assert dto.status == ActivityStatus.IN_PROGRESS
        assert dto.end_event_id is None
        assert dto.duration_ms is None


class TestRetryDecorator:
    """Tests for the retry_on_connection_failure decorator."""

    def test_retry_success_on_first_try(self) -> None:
        """Test function succeeds without retries."""
        from ara.storage.client import retry_on_connection_failure

        call_count = 0

        @retry_on_connection_failure(max_retries=3)
        def successful_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()

        assert result == "success"
        assert call_count == 1

    def test_retry_success_after_failures(self) -> None:
        """Test function succeeds after transient failures."""
        from pymongo.errors import ConnectionFailure

        from ara.storage.client import retry_on_connection_failure

        call_count = 0

        @retry_on_connection_failure(max_retries=5, base_delay=0.01)
        def flaky_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionFailure("Connection lost")
            return "success"

        result = flaky_func()

        assert result == "success"
        assert call_count == 3

    def test_retry_exhausted(self) -> None:
        """Test function raises after max retries."""
        from pymongo.errors import ConnectionFailure

        from ara.storage.client import retry_on_connection_failure

        @retry_on_connection_failure(max_retries=2, base_delay=0.01)
        def always_fails() -> str:
            raise ConnectionFailure("Persistent failure")

        with pytest.raises(ConnectionFailure):
            always_fails()


class TestMongoStorageClient:
    """Tests for MongoStorageClient."""

    @patch("ara.storage.client.MongoClient")
    def test_connect_success(self, mock_mongo_client: MagicMock) -> None:
        """Test successful connection to MongoDB."""
        from ara.storage.client import MongoStorageClient

        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance

        client = MongoStorageClient(uri="mongodb://localhost:27017")
        client.connect()

        assert client.is_connected()
        mock_client_instance.admin.command.assert_called_with("ping")

    @patch("ara.storage.client.MongoClient")
    def test_connect_failure(self, mock_mongo_client: MagicMock) -> None:
        """Test connection failure handling."""
        from pymongo.errors import ConnectionFailure

        from ara.storage.client import MongoStorageClient

        mock_mongo_client.side_effect = ConnectionFailure("Connection refused")

        client = MongoStorageClient(uri="mongodb://localhost:27017")

        with pytest.raises(ConnectionFailure):
            client.connect()

        assert not client.is_connected()

    @patch("ara.storage.client.MongoClient")
    def test_disconnect(self, mock_mongo_client: MagicMock) -> None:
        """Test disconnection from MongoDB."""
        from ara.storage.client import MongoStorageClient

        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance

        client = MongoStorageClient()
        client.connect()
        client.disconnect()

        mock_client_instance.close.assert_called_once()
        assert not client.is_connected()

    @patch("ara.storage.client.MongoClient")
    def test_context_manager(self, mock_mongo_client: MagicMock) -> None:
        """Test client works as context manager."""
        from ara.storage.client import MongoStorageClient

        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance

        with MongoStorageClient() as client:
            assert client.is_connected()

        mock_client_instance.close.assert_called_once()

    def test_interactions_property_raises_when_not_connected(self) -> None:
        """Test accessing interactions raises when not connected."""
        from ara.storage.client import MongoStorageClient

        client = MongoStorageClient()

        with pytest.raises(RuntimeError, match="Not connected"):
            _ = client.interactions
