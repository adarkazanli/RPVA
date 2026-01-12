"""Unit tests for Interaction and Session entities."""

import uuid
from datetime import UTC, datetime

import pytest

from ara.logger.interaction import (
    Interaction,
    InteractionLogger,
    OperationMode,
    ResponseSource,
    Session,
    SessionState,
)


class TestInteraction:
    """Tests for Interaction entity."""

    def test_create_interaction(self) -> None:
        """Test creating an interaction with all fields."""
        interaction = Interaction(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            timestamp=datetime.now(UTC),
            device_id="pi4-kitchen",
            wake_word_confidence=0.95,
            audio_duration_ms=2500,
            transcript="what time is it",
            transcript_confidence=0.92,
            intent="general_question",
            intent_confidence=0.85,
            entities={},
            response="It's 3:30 PM",
            response_source=ResponseSource.LOCAL_LLM,
            latency_ms={"stt": 450, "llm": 800, "tts": 200, "total": 1450},
            mode=OperationMode.OFFLINE,
            error=None,
        )
        assert interaction.device_id == "pi4-kitchen"
        assert interaction.transcript == "what time is it"
        assert interaction.response_source == ResponseSource.LOCAL_LLM

    def test_interaction_with_error(self) -> None:
        """Test creating an interaction with an error."""
        interaction = Interaction(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            timestamp=datetime.now(UTC),
            device_id="pi4-kitchen",
            wake_word_confidence=0.9,
            audio_duration_ms=1000,
            transcript="",
            transcript_confidence=0.0,
            intent="unknown",
            intent_confidence=0.0,
            entities={},
            response="",
            response_source=ResponseSource.LOCAL_LLM,
            latency_ms={"total": 500},
            mode=OperationMode.OFFLINE,
            error="STT transcription failed",
        )
        assert interaction.error is not None
        assert "STT" in interaction.error

    def test_interaction_with_entities(self) -> None:
        """Test interaction with extracted entities."""
        interaction = Interaction(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            timestamp=datetime.now(UTC),
            device_id="pi4-kitchen",
            wake_word_confidence=0.95,
            audio_duration_ms=3000,
            transcript="set a timer for 5 minutes",
            transcript_confidence=0.95,
            intent="timer_set",
            intent_confidence=0.92,
            entities={"duration": "5 minutes"},
            response="Timer set for 5 minutes",
            response_source=ResponseSource.SYSTEM,
            latency_ms={"stt": 400, "llm": 50, "tts": 180, "total": 630},
            mode=OperationMode.OFFLINE,
            error=None,
        )
        assert interaction.entities["duration"] == "5 minutes"
        assert interaction.response_source == ResponseSource.SYSTEM

    def test_interaction_to_dict(self) -> None:
        """Test converting interaction to dictionary."""
        interaction_id = uuid.uuid4()
        session_id = uuid.uuid4()
        timestamp = datetime.now(UTC)

        interaction = Interaction(
            id=interaction_id,
            session_id=session_id,
            timestamp=timestamp,
            device_id="pi4-kitchen",
            wake_word_confidence=0.95,
            audio_duration_ms=2500,
            transcript="hello",
            transcript_confidence=0.9,
            intent="general_question",
            intent_confidence=0.8,
            entities={},
            response="Hi there!",
            response_source=ResponseSource.LOCAL_LLM,
            latency_ms={"total": 1000},
            mode=OperationMode.OFFLINE,
            error=None,
        )

        data = interaction.to_dict()
        assert data["id"] == str(interaction_id)
        assert data["session_id"] == str(session_id)
        assert data["device_id"] == "pi4-kitchen"
        assert data["transcript"] == "hello"

    def test_interaction_from_dict(self) -> None:
        """Test creating interaction from dictionary."""
        interaction_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        data = {
            "id": interaction_id,
            "session_id": session_id,
            "timestamp": "2024-01-15T10:30:00+00:00",
            "device_id": "pi4-kitchen",
            "wake_word_confidence": 0.95,
            "audio_duration_ms": 2500,
            "transcript": "hello",
            "transcript_confidence": 0.9,
            "intent": "general_question",
            "intent_confidence": 0.8,
            "entities": {},
            "response": "Hi there!",
            "response_source": "local_llm",
            "latency_ms": {"total": 1000},
            "mode": "offline",
            "error": None,
        }

        interaction = Interaction.from_dict(data)
        assert str(interaction.id) == interaction_id
        assert interaction.transcript == "hello"


class TestResponseSource:
    """Tests for ResponseSource enum."""

    def test_response_source_values(self) -> None:
        """Test all response source values exist."""
        assert ResponseSource.LOCAL_LLM.value == "local_llm"
        assert ResponseSource.CLOUD_API.value == "cloud_api"
        assert ResponseSource.SYSTEM.value == "system"


class TestOperationMode:
    """Tests for OperationMode enum."""

    def test_operation_mode_values(self) -> None:
        """Test all operation mode values exist."""
        assert OperationMode.OFFLINE.value == "offline"
        assert OperationMode.ONLINE_LOCAL.value == "online_local"
        assert OperationMode.ONLINE_CLOUD.value == "online_cloud"


class TestSession:
    """Tests for Session entity."""

    def test_create_session(self) -> None:
        """Test creating a session."""
        session = Session(
            id=uuid.uuid4(),
            device_id="pi4-kitchen",
            started_at=datetime.now(UTC),
            ended_at=None,
            interaction_count=0,
            mode=OperationMode.OFFLINE,
            state=SessionState.ACTIVE,
        )
        assert session.device_id == "pi4-kitchen"
        assert session.state == SessionState.ACTIVE
        assert session.ended_at is None

    def test_session_end(self) -> None:
        """Test ending a session."""
        session = Session(
            id=uuid.uuid4(),
            device_id="pi4-kitchen",
            started_at=datetime.now(UTC),
            ended_at=None,
            interaction_count=5,
            mode=OperationMode.OFFLINE,
            state=SessionState.ACTIVE,
        )

        session.end()
        assert session.state == SessionState.ENDED
        assert session.ended_at is not None

    def test_session_timeout(self) -> None:
        """Test session timeout."""
        session = Session(
            id=uuid.uuid4(),
            device_id="pi4-kitchen",
            started_at=datetime.now(UTC),
            ended_at=None,
            interaction_count=3,
            mode=OperationMode.OFFLINE,
            state=SessionState.ACTIVE,
        )

        session.timeout()
        assert session.state == SessionState.TIMEOUT


class TestSessionState:
    """Tests for SessionState enum."""

    def test_session_state_values(self) -> None:
        """Test all session state values exist."""
        assert SessionState.CREATED.value == "created"
        assert SessionState.ACTIVE.value == "active"
        assert SessionState.TIMEOUT.value == "timeout"
        assert SessionState.ENDED.value == "ended"


class TestInteractionLogger:
    """Tests for InteractionLogger."""

    @pytest.fixture
    def logger(self, tmp_path) -> InteractionLogger:
        """Create an InteractionLogger with temp storage."""
        return InteractionLogger(
            device_id="test-device",
            storage_path=tmp_path / "logs",
        )

    def test_log_interaction(self, logger: InteractionLogger) -> None:
        """Test logging an interaction."""
        interaction = logger.log(
            transcript="what time is it",
            response="It's 3:30 PM",
            intent="general_question",
            latency_ms={"stt": 450, "llm": 800, "total": 1250},
        )

        assert interaction.transcript == "what time is it"
        assert interaction.device_id == "test-device"
        assert interaction.session_id is not None

    def test_log_creates_session(self, logger: InteractionLogger) -> None:
        """Test that logging creates a session if none exists."""
        assert logger.current_session is None

        logger.log(
            transcript="hello",
            response="Hi!",
            intent="general_question",
            latency_ms={"total": 500},
        )

        assert logger.current_session is not None
        assert logger.current_session.interaction_count == 1

    def test_log_increments_session_count(self, logger: InteractionLogger) -> None:
        """Test that logging increments session interaction count."""
        logger.log(transcript="one", response="1", intent="general_question", latency_ms={"total": 100})
        logger.log(transcript="two", response="2", intent="general_question", latency_ms={"total": 100})
        logger.log(transcript="three", response="3", intent="general_question", latency_ms={"total": 100})

        assert logger.current_session.interaction_count == 3

    def test_get_recent_interactions(self, logger: InteractionLogger) -> None:
        """Test getting recent interactions."""
        for i in range(5):
            logger.log(
                transcript=f"question {i}",
                response=f"answer {i}",
                intent="general_question",
                latency_ms={"total": 100},
            )

        recent = logger.get_recent(limit=3)
        assert len(recent) == 3
        # Most recent first
        assert recent[0].transcript == "question 4"

    def test_get_interactions_by_date(self, logger: InteractionLogger) -> None:
        """Test getting interactions by date."""
        logger.log(
            transcript="today's question",
            response="today's answer",
            intent="general_question",
            latency_ms={"total": 100},
        )

        today = datetime.now(UTC).date()
        interactions = logger.get_by_date(today)

        assert len(interactions) >= 1
        assert interactions[0].transcript == "today's question"
