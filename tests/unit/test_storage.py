"""Unit tests for storage layer."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from ara.logger.interaction import Interaction, OperationMode, ResponseSource
from ara.logger.storage import (
    InteractionStorage,
    JSONLWriter,
    SQLiteStorage,
)


class TestSQLiteStorage:
    """Tests for SQLite storage backend."""

    @pytest.fixture
    def storage(self, tmp_path) -> SQLiteStorage:
        """Create a SQLite storage instance."""
        db_path = tmp_path / "test.db"
        return SQLiteStorage(db_path)

    @pytest.fixture
    def sample_interaction(self) -> Interaction:
        """Create a sample interaction."""
        return Interaction(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            timestamp=datetime.now(UTC),
            device_id="test-device",
            wake_word_confidence=0.95,
            audio_duration_ms=2500,
            transcript="what time is it",
            transcript_confidence=0.9,
            intent="general_question",
            intent_confidence=0.85,
            entities={},
            response="It's 3:30 PM",
            response_source=ResponseSource.LOCAL_LLM,
            latency_ms={"stt": 450, "llm": 800, "total": 1250},
            mode=OperationMode.OFFLINE,
            error=None,
        )

    def test_save_interaction(
        self, storage: SQLiteStorage, sample_interaction: Interaction
    ) -> None:
        """Test saving an interaction."""
        storage.save(sample_interaction)

        # Verify it was saved
        retrieved = storage.get(sample_interaction.id)
        assert retrieved is not None
        assert retrieved.transcript == sample_interaction.transcript

    def test_get_nonexistent_interaction(self, storage: SQLiteStorage) -> None:
        """Test getting a nonexistent interaction."""
        result = storage.get(uuid.uuid4())
        assert result is None

    def test_get_by_session(self, storage: SQLiteStorage, sample_interaction: Interaction) -> None:
        """Test getting interactions by session."""
        # Save multiple interactions in same session
        session_id = sample_interaction.session_id

        storage.save(sample_interaction)

        interaction2 = Interaction(
            id=uuid.uuid4(),
            session_id=session_id,
            timestamp=datetime.now(UTC),
            device_id="test-device",
            wake_word_confidence=0.95,
            audio_duration_ms=2000,
            transcript="another question",
            transcript_confidence=0.9,
            intent="general_question",
            intent_confidence=0.85,
            entities={},
            response="Another answer",
            response_source=ResponseSource.LOCAL_LLM,
            latency_ms={"total": 1000},
            mode=OperationMode.OFFLINE,
            error=None,
        )
        storage.save(interaction2)

        results = storage.get_by_session(session_id)
        assert len(results) == 2

    def test_get_by_date_range(
        self, storage: SQLiteStorage, sample_interaction: Interaction
    ) -> None:
        """Test getting interactions by date range."""
        storage.save(sample_interaction)

        start = datetime.now(UTC) - timedelta(hours=1)
        end = datetime.now(UTC) + timedelta(hours=1)

        results = storage.get_by_date_range(start, end)
        assert len(results) >= 1

    def test_get_by_device(self, storage: SQLiteStorage, sample_interaction: Interaction) -> None:
        """Test getting interactions by device."""
        storage.save(sample_interaction)

        results = storage.get_by_device("test-device")
        assert len(results) >= 1
        assert all(r.device_id == "test-device" for r in results)

    def test_get_recent(self, storage: SQLiteStorage) -> None:
        """Test getting recent interactions."""
        session_id = uuid.uuid4()

        for i in range(10):
            interaction = Interaction(
                id=uuid.uuid4(),
                session_id=session_id,
                timestamp=datetime.now(UTC),
                device_id="test-device",
                wake_word_confidence=0.95,
                audio_duration_ms=2000,
                transcript=f"question {i}",
                transcript_confidence=0.9,
                intent="general_question",
                intent_confidence=0.85,
                entities={},
                response=f"answer {i}",
                response_source=ResponseSource.LOCAL_LLM,
                latency_ms={"total": 1000},
                mode=OperationMode.OFFLINE,
                error=None,
            )
            storage.save(interaction)

        recent = storage.get_recent(limit=5)
        assert len(recent) == 5

    def test_count_by_date(self, storage: SQLiteStorage, sample_interaction: Interaction) -> None:
        """Test counting interactions by date."""
        storage.save(sample_interaction)

        today = datetime.now(UTC).date()
        count = storage.count_by_date(today)
        assert count >= 1

    def test_get_intent_counts(self, storage: SQLiteStorage) -> None:
        """Test getting intent counts."""
        session_id = uuid.uuid4()

        intents = [
            "general_question",
            "timer_set",
            "general_question",
            "timer_set",
            "general_question",
        ]
        for i, intent in enumerate(intents):
            interaction = Interaction(
                id=uuid.uuid4(),
                session_id=session_id,
                timestamp=datetime.now(UTC),
                device_id="test-device",
                wake_word_confidence=0.95,
                audio_duration_ms=2000,
                transcript=f"q{i}",
                transcript_confidence=0.9,
                intent=intent,
                intent_confidence=0.85,
                entities={},
                response=f"a{i}",
                response_source=ResponseSource.LOCAL_LLM,
                latency_ms={"total": 1000},
                mode=OperationMode.OFFLINE,
                error=None,
            )
            storage.save(interaction)

        today = datetime.now(UTC).date()
        counts = storage.get_intent_counts(today)

        assert counts.get("general_question", 0) >= 3
        assert counts.get("timer_set", 0) >= 2

    def test_get_average_latency(self, storage: SQLiteStorage) -> None:
        """Test getting average latency."""
        session_id = uuid.uuid4()

        for latency in [1000, 1200, 1400, 1600, 1800]:
            interaction = Interaction(
                id=uuid.uuid4(),
                session_id=session_id,
                timestamp=datetime.now(UTC),
                device_id="test-device",
                wake_word_confidence=0.95,
                audio_duration_ms=2000,
                transcript="q",
                transcript_confidence=0.9,
                intent="general_question",
                intent_confidence=0.85,
                entities={},
                response="a",
                response_source=ResponseSource.LOCAL_LLM,
                latency_ms={"total": latency},
                mode=OperationMode.OFFLINE,
                error=None,
            )
            storage.save(interaction)

        today = datetime.now(UTC).date()
        avg = storage.get_average_latency(today)

        # Average of 1000, 1200, 1400, 1600, 1800 = 1400
        assert 1300 <= avg <= 1500

    def test_database_uses_wal_mode(self, storage: SQLiteStorage) -> None:
        """Test that database uses WAL mode."""
        # WAL mode should be enabled for better concurrent access
        assert storage.is_wal_mode_enabled()


class TestJSONLWriter:
    """Tests for JSONL file writer."""

    @pytest.fixture
    def writer(self, tmp_path) -> JSONLWriter:
        """Create a JSONL writer instance."""
        return JSONLWriter(tmp_path / "logs")

    @pytest.fixture
    def sample_interaction(self) -> Interaction:
        """Create a sample interaction."""
        return Interaction(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            timestamp=datetime.now(UTC),
            device_id="test-device",
            wake_word_confidence=0.95,
            audio_duration_ms=2500,
            transcript="what time is it",
            transcript_confidence=0.9,
            intent="general_question",
            intent_confidence=0.85,
            entities={},
            response="It's 3:30 PM",
            response_source=ResponseSource.LOCAL_LLM,
            latency_ms={"stt": 450, "llm": 800, "total": 1250},
            mode=OperationMode.OFFLINE,
            error=None,
        )

    def test_write_interaction(self, writer: JSONLWriter, sample_interaction: Interaction) -> None:
        """Test writing an interaction to JSONL."""
        writer.write(sample_interaction)

        # Check file was created
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        log_file = writer.log_dir / f"{today}.jsonl"
        assert log_file.exists()

    def test_append_to_existing_file(
        self, writer: JSONLWriter, sample_interaction: Interaction
    ) -> None:
        """Test appending to existing JSONL file."""
        writer.write(sample_interaction)

        interaction2 = Interaction(
            id=uuid.uuid4(),
            session_id=sample_interaction.session_id,
            timestamp=datetime.now(UTC),
            device_id="test-device",
            wake_word_confidence=0.95,
            audio_duration_ms=2000,
            transcript="another question",
            transcript_confidence=0.9,
            intent="general_question",
            intent_confidence=0.85,
            entities={},
            response="Another answer",
            response_source=ResponseSource.LOCAL_LLM,
            latency_ms={"total": 1000},
            mode=OperationMode.OFFLINE,
            error=None,
        )
        writer.write(interaction2)

        # Check both lines exist
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        log_file = writer.log_dir / f"{today}.jsonl"

        with open(log_file) as f:
            lines = f.readlines()

        assert len(lines) == 2

    def test_read_interactions(self, writer: JSONLWriter, sample_interaction: Interaction) -> None:
        """Test reading interactions from JSONL."""
        writer.write(sample_interaction)

        today = datetime.now(UTC).date()
        interactions = writer.read(today)

        assert len(interactions) == 1
        assert interactions[0].transcript == sample_interaction.transcript

    def test_read_nonexistent_date(self, writer: JSONLWriter) -> None:
        """Test reading from nonexistent date."""
        from datetime import date

        interactions = writer.read(date(2020, 1, 1))
        assert interactions == []

    def test_json_format_valid(self, writer: JSONLWriter, sample_interaction: Interaction) -> None:
        """Test that written JSON is valid."""
        writer.write(sample_interaction)

        today = datetime.now(UTC).strftime("%Y-%m-%d")
        log_file = writer.log_dir / f"{today}.jsonl"

        with open(log_file) as f:
            line = f.readline()
            data = json.loads(line)

        assert data["transcript"] == sample_interaction.transcript
        assert data["device_id"] == sample_interaction.device_id


class TestInteractionStorage:
    """Tests for combined storage interface."""

    @pytest.fixture
    def storage(self, tmp_path) -> InteractionStorage:
        """Create an InteractionStorage instance."""
        return InteractionStorage(
            db_path=tmp_path / "test.db",
            log_dir=tmp_path / "logs",
        )

    @pytest.fixture
    def sample_interaction(self) -> Interaction:
        """Create a sample interaction."""
        return Interaction(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            timestamp=datetime.now(UTC),
            device_id="test-device",
            wake_word_confidence=0.95,
            audio_duration_ms=2500,
            transcript="what time is it",
            transcript_confidence=0.9,
            intent="general_question",
            intent_confidence=0.85,
            entities={},
            response="It's 3:30 PM",
            response_source=ResponseSource.LOCAL_LLM,
            latency_ms={"stt": 450, "llm": 800, "total": 1250},
            mode=OperationMode.OFFLINE,
            error=None,
        )

    def test_save_to_both_backends(
        self, storage: InteractionStorage, sample_interaction: Interaction
    ) -> None:
        """Test saving writes to both SQLite and JSONL."""
        storage.save(sample_interaction)

        # Verify in SQLite
        retrieved = storage.sqlite.get(sample_interaction.id)
        assert retrieved is not None

        # Verify in JSONL
        today = datetime.now(UTC).date()
        jsonl_data = storage.jsonl.read(today)
        assert len(jsonl_data) >= 1

    def test_query_from_sqlite(
        self, storage: InteractionStorage, sample_interaction: Interaction
    ) -> None:
        """Test queries use SQLite backend."""
        storage.save(sample_interaction)

        results = storage.get_recent(limit=10)
        assert len(results) >= 1
