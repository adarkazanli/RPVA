"""Interaction and Session entities for conversation logging.

Defines data structures for logging voice interactions and managing sessions.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    from .storage import InteractionStorage


class ResponseSource(Enum):
    """Source of the response."""

    LOCAL_LLM = "local_llm"
    CLOUD_API = "cloud_api"
    SYSTEM = "system"


class OperationMode(Enum):
    """Operation mode during interaction."""

    OFFLINE = "offline"
    ONLINE_LOCAL = "online_local"
    ONLINE_CLOUD = "online_cloud"


class SessionState(Enum):
    """State of a session."""

    CREATED = "created"
    ACTIVE = "active"
    TIMEOUT = "timeout"
    ENDED = "ended"


@dataclass
class Interaction:
    """A single user query and system response pair.

    Attributes:
        id: Unique interaction identifier.
        session_id: Parent session reference.
        timestamp: UTC timestamp of interaction start.
        device_id: Device identifier.
        wake_word_confidence: Wake word detection confidence.
        audio_duration_ms: Duration of user audio input.
        transcript: STT transcription result.
        transcript_confidence: Transcription confidence.
        intent: Classified intent.
        intent_confidence: Intent classification confidence.
        entities: Extracted entities.
        response: LLM-generated response text.
        response_source: Source of the response.
        latency_ms: Component latencies.
        mode: Operation mode during interaction.
        error: Error message if interaction failed.
    """

    id: UUID
    session_id: UUID
    timestamp: datetime
    device_id: str
    wake_word_confidence: float
    audio_duration_ms: int
    transcript: str
    transcript_confidence: float
    intent: str
    intent_confidence: float
    entities: dict[str, Any]
    response: str
    response_source: ResponseSource
    latency_ms: dict[str, int]
    mode: OperationMode
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert interaction to dictionary for serialization."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "timestamp": self.timestamp.isoformat(),
            "device_id": self.device_id,
            "wake_word_confidence": self.wake_word_confidence,
            "audio_duration_ms": self.audio_duration_ms,
            "transcript": self.transcript,
            "transcript_confidence": self.transcript_confidence,
            "intent": self.intent,
            "intent_confidence": self.intent_confidence,
            "entities": self.entities,
            "response": self.response,
            "response_source": self.response_source.value,
            "latency_ms": self.latency_ms,
            "mode": self.mode.value,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Interaction":
        """Create interaction from dictionary."""
        return cls(
            id=UUID(data["id"]),
            session_id=UUID(data["session_id"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            device_id=data["device_id"],
            wake_word_confidence=data["wake_word_confidence"],
            audio_duration_ms=data["audio_duration_ms"],
            transcript=data["transcript"],
            transcript_confidence=data["transcript_confidence"],
            intent=data["intent"],
            intent_confidence=data["intent_confidence"],
            entities=data.get("entities", {}),
            response=data["response"],
            response_source=ResponseSource(data["response_source"]),
            latency_ms=data["latency_ms"],
            mode=OperationMode(data["mode"]),
            error=data.get("error"),
        )


@dataclass
class Session:
    """A grouping of related interactions.

    Attributes:
        id: Unique session identifier.
        device_id: Device identifier.
        started_at: First interaction timestamp.
        ended_at: Last interaction + timeout.
        interaction_count: Number of interactions.
        mode: Session mode.
        state: Current session state.
    """

    id: UUID
    device_id: str
    started_at: datetime
    ended_at: datetime | None
    interaction_count: int
    mode: OperationMode
    state: SessionState

    def end(self) -> None:
        """End the session."""
        self.state = SessionState.ENDED
        self.ended_at = datetime.now(UTC)

    def timeout(self) -> None:
        """Mark session as timed out."""
        self.state = SessionState.TIMEOUT
        self.ended_at = datetime.now(UTC)


class InteractionLogger:
    """Logs voice interactions to storage.

    Manages sessions and persists interactions to both SQLite and JSONL.
    """

    def __init__(
        self,
        device_id: str,
        storage: "InteractionStorage | None" = None,
        storage_path: Path | None = None,
    ) -> None:
        """Initialize the interaction logger.

        Args:
            device_id: Device identifier for all logged interactions.
            storage: Optional pre-configured storage instance.
            storage_path: Path for storage if no storage provided.
        """
        self._device_id = device_id
        self._current_session: Session | None = None
        self._session_timeout_minutes = 5

        if storage is not None:
            self._storage = storage
        elif storage_path is not None:
            from .storage import InteractionStorage

            storage_path.mkdir(parents=True, exist_ok=True)
            self._storage = InteractionStorage(
                db_path=storage_path / "interactions.db",
                log_dir=storage_path / "jsonl",
            )
        else:
            # In-memory storage for testing
            self._storage = None
            self._interactions: list[Interaction] = []

    @property
    def current_session(self) -> Session | None:
        """Get the current session."""
        return self._current_session

    @property
    def device_id(self) -> str:
        """Get the device ID."""
        return self._device_id

    def log(
        self,
        transcript: str,
        response: str,
        intent: str,
        latency_ms: dict[str, int],
        wake_word_confidence: float = 0.95,
        audio_duration_ms: int = 2000,
        transcript_confidence: float = 0.9,
        intent_confidence: float = 0.85,
        entities: dict[str, Any] | None = None,
        response_source: ResponseSource = ResponseSource.LOCAL_LLM,
        mode: OperationMode = OperationMode.OFFLINE,
        error: str | None = None,
    ) -> Interaction:
        """Log an interaction.

        Args:
            transcript: User's spoken text.
            response: Assistant's response.
            intent: Classified intent.
            latency_ms: Component latencies.
            wake_word_confidence: Wake word detection confidence.
            audio_duration_ms: Duration of user audio.
            transcript_confidence: Transcription confidence.
            intent_confidence: Intent classification confidence.
            entities: Extracted entities.
            response_source: Source of the response.
            mode: Operation mode.
            error: Error message if failed.

        Returns:
            The logged Interaction.
        """
        # Ensure we have a session
        if self._current_session is None:
            self._start_session(mode)

        interaction = Interaction(
            id=uuid.uuid4(),
            session_id=self._current_session.id,
            timestamp=datetime.now(UTC),
            device_id=self._device_id,
            wake_word_confidence=wake_word_confidence,
            audio_duration_ms=audio_duration_ms,
            transcript=transcript,
            transcript_confidence=transcript_confidence,
            intent=intent,
            intent_confidence=intent_confidence,
            entities=entities or {},
            response=response,
            response_source=response_source,
            latency_ms=latency_ms,
            mode=mode,
            error=error,
        )

        # Update session
        self._current_session.interaction_count += 1

        # Persist
        if self._storage is not None:
            self._storage.save(interaction)
        else:
            self._interactions.append(interaction)

        return interaction

    def _start_session(self, mode: OperationMode) -> Session:
        """Start a new session."""
        self._current_session = Session(
            id=uuid.uuid4(),
            device_id=self._device_id,
            started_at=datetime.now(UTC),
            ended_at=None,
            interaction_count=0,
            mode=mode,
            state=SessionState.ACTIVE,
        )
        return self._current_session

    def end_session(self) -> None:
        """End the current session."""
        if self._current_session is not None:
            self._current_session.end()
            self._current_session = None

    def get_recent(self, limit: int = 10) -> list[Interaction]:
        """Get recent interactions.

        Args:
            limit: Maximum number of interactions to return.

        Returns:
            List of recent interactions, most recent first.
        """
        if self._storage is not None:
            return self._storage.get_recent(limit=limit)
        else:
            return list(reversed(self._interactions[-limit:]))

    def get_by_date(self, target_date: date) -> list[Interaction]:
        """Get interactions by date.

        Args:
            target_date: Date to get interactions for.

        Returns:
            List of interactions from that date.
        """
        if self._storage is not None:
            start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=UTC)
            end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=UTC)
            return self._storage.sqlite.get_by_date_range(start, end)
        else:
            return [i for i in self._interactions if i.timestamp.date() == target_date]


__all__ = [
    "Interaction",
    "InteractionLogger",
    "OperationMode",
    "ResponseSource",
    "Session",
    "SessionState",
]
