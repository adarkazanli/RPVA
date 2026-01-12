"""Storage layer for interaction logging.

Provides SQLite and JSONL storage backends for interaction data.
"""

import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import UUID

from .interaction import Interaction, OperationMode, ResponseSource


class SQLiteStorage:
    """SQLite storage backend for interactions.

    Uses WAL mode for better concurrent access and performance.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize SQLite storage.

        Args:
            db_path: Path to the SQLite database file.
        """
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrency
        self._conn.execute("PRAGMA journal_mode=WAL")

        self._create_tables()

    def _create_tables(self) -> None:
        """Create database tables."""
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS interactions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                device_id TEXT NOT NULL,
                wake_word_confidence REAL NOT NULL,
                audio_duration_ms INTEGER NOT NULL,
                transcript TEXT NOT NULL,
                transcript_confidence REAL NOT NULL,
                intent TEXT NOT NULL,
                intent_confidence REAL NOT NULL,
                entities TEXT,
                response TEXT NOT NULL,
                response_source TEXT NOT NULL,
                latency_ms TEXT NOT NULL,
                mode TEXT NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_interactions_session
                ON interactions(session_id);
            CREATE INDEX IF NOT EXISTS idx_interactions_timestamp
                ON interactions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_interactions_device
                ON interactions(device_id);
            CREATE INDEX IF NOT EXISTS idx_interactions_intent
                ON interactions(intent);

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                interaction_count INTEGER NOT NULL,
                mode TEXT NOT NULL,
                state TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS timers (
                id TEXT PRIMARY KEY,
                name TEXT,
                duration_seconds INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'running',
                alert_played INTEGER NOT NULL DEFAULT 0,
                created_by_interaction TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id TEXT PRIMARY KEY,
                message TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                recurrence TEXT DEFAULT 'none',
                status TEXT NOT NULL DEFAULT 'pending',
                triggered_at TEXT,
                created_by_interaction TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_timers_status ON timers(status);
            CREATE INDEX IF NOT EXISTS idx_reminders_remind_at ON reminders(remind_at);
            """
        )
        self._conn.commit()

    def save(self, interaction: Interaction) -> None:
        """Save an interaction to the database.

        Args:
            interaction: The interaction to save.
        """
        self._conn.execute(
            """
            INSERT INTO interactions (
                id, session_id, timestamp, device_id, wake_word_confidence,
                audio_duration_ms, transcript, transcript_confidence, intent,
                intent_confidence, entities, response, response_source,
                latency_ms, mode, error, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(interaction.id),
                str(interaction.session_id),
                interaction.timestamp.isoformat(),
                interaction.device_id,
                interaction.wake_word_confidence,
                interaction.audio_duration_ms,
                interaction.transcript,
                interaction.transcript_confidence,
                interaction.intent,
                interaction.intent_confidence,
                json.dumps(interaction.entities),
                interaction.response,
                interaction.response_source.value,
                json.dumps(interaction.latency_ms),
                interaction.mode.value,
                interaction.error,
                datetime.now(UTC).isoformat(),
            ),
        )
        self._conn.commit()

    def get(self, interaction_id: UUID) -> Interaction | None:
        """Get an interaction by ID.

        Args:
            interaction_id: The interaction ID.

        Returns:
            The Interaction or None if not found.
        """
        cursor = self._conn.execute(
            "SELECT * FROM interactions WHERE id = ?",
            (str(interaction_id),),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_interaction(row)

    def get_by_session(self, session_id: UUID) -> list[Interaction]:
        """Get all interactions in a session.

        Args:
            session_id: The session ID.

        Returns:
            List of interactions.
        """
        cursor = self._conn.execute(
            "SELECT * FROM interactions WHERE session_id = ? ORDER BY timestamp",
            (str(session_id),),
        )
        return [self._row_to_interaction(row) for row in cursor.fetchall()]

    def get_by_date_range(
        self, start: datetime, end: datetime
    ) -> list[Interaction]:
        """Get interactions within a date range.

        Args:
            start: Start datetime.
            end: End datetime.

        Returns:
            List of interactions.
        """
        cursor = self._conn.execute(
            """
            SELECT * FROM interactions
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp DESC
            """,
            (start.isoformat(), end.isoformat()),
        )
        return [self._row_to_interaction(row) for row in cursor.fetchall()]

    def get_by_device(
        self, device_id: str, limit: int = 100
    ) -> list[Interaction]:
        """Get interactions by device.

        Args:
            device_id: The device ID.
            limit: Maximum number to return.

        Returns:
            List of interactions.
        """
        cursor = self._conn.execute(
            """
            SELECT * FROM interactions
            WHERE device_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (device_id, limit),
        )
        return [self._row_to_interaction(row) for row in cursor.fetchall()]

    def get_recent(self, limit: int = 10) -> list[Interaction]:
        """Get recent interactions.

        Args:
            limit: Maximum number to return.

        Returns:
            List of interactions, most recent first.
        """
        cursor = self._conn.execute(
            """
            SELECT * FROM interactions
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_interaction(row) for row in cursor.fetchall()]

    def count_by_date(self, target_date: date) -> int:
        """Count interactions on a specific date.

        Args:
            target_date: The date to count.

        Returns:
            Number of interactions.
        """
        start = datetime.combine(target_date, datetime.min.time()).replace(
            tzinfo=UTC
        )
        end = datetime.combine(target_date, datetime.max.time()).replace(
            tzinfo=UTC
        )

        cursor = self._conn.execute(
            """
            SELECT COUNT(*) FROM interactions
            WHERE timestamp >= ? AND timestamp <= ?
            """,
            (start.isoformat(), end.isoformat()),
        )
        return cursor.fetchone()[0]

    def get_intent_counts(self, target_date: date) -> dict[str, int]:
        """Get intent counts for a specific date.

        Args:
            target_date: The date to get counts for.

        Returns:
            Dictionary of intent to count.
        """
        start = datetime.combine(target_date, datetime.min.time()).replace(
            tzinfo=UTC
        )
        end = datetime.combine(target_date, datetime.max.time()).replace(
            tzinfo=UTC
        )

        cursor = self._conn.execute(
            """
            SELECT intent, COUNT(*) as count FROM interactions
            WHERE timestamp >= ? AND timestamp <= ?
            GROUP BY intent
            ORDER BY count DESC
            """,
            (start.isoformat(), end.isoformat()),
        )

        return {row["intent"]: row["count"] for row in cursor.fetchall()}

    def get_average_latency(self, target_date: date) -> float:
        """Get average total latency for a specific date.

        Args:
            target_date: The date to calculate for.

        Returns:
            Average latency in ms.
        """
        start = datetime.combine(target_date, datetime.min.time()).replace(
            tzinfo=UTC
        )
        end = datetime.combine(target_date, datetime.max.time()).replace(
            tzinfo=UTC
        )

        cursor = self._conn.execute(
            """
            SELECT latency_ms FROM interactions
            WHERE timestamp >= ? AND timestamp <= ?
            """,
            (start.isoformat(), end.isoformat()),
        )

        latencies = []
        for row in cursor.fetchall():
            latency_data = json.loads(row["latency_ms"])
            if "total" in latency_data:
                latencies.append(latency_data["total"])

        if not latencies:
            return 0.0

        return sum(latencies) / len(latencies)

    def is_wal_mode_enabled(self) -> bool:
        """Check if WAL mode is enabled."""
        cursor = self._conn.execute("PRAGMA journal_mode")
        return cursor.fetchone()[0].lower() == "wal"

    def _row_to_interaction(self, row: sqlite3.Row) -> Interaction:
        """Convert a database row to an Interaction."""
        return Interaction(
            id=UUID(row["id"]),
            session_id=UUID(row["session_id"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            device_id=row["device_id"],
            wake_word_confidence=row["wake_word_confidence"],
            audio_duration_ms=row["audio_duration_ms"],
            transcript=row["transcript"],
            transcript_confidence=row["transcript_confidence"],
            intent=row["intent"],
            intent_confidence=row["intent_confidence"],
            entities=json.loads(row["entities"]) if row["entities"] else {},
            response=row["response"],
            response_source=ResponseSource(row["response_source"]),
            latency_ms=json.loads(row["latency_ms"]),
            mode=OperationMode(row["mode"]),
            error=row["error"],
        )

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()


class JSONLWriter:
    """JSONL file writer for interaction logs.

    Writes each interaction as a JSON line to daily log files.
    """

    def __init__(self, log_dir: Path) -> None:
        """Initialize JSONL writer.

        Args:
            log_dir: Directory for log files.
        """
        self._log_dir = log_dir
        log_dir.mkdir(parents=True, exist_ok=True)

    @property
    def log_dir(self) -> Path:
        """Get the log directory."""
        return self._log_dir

    def write(self, interaction: Interaction) -> None:
        """Write an interaction to the daily log file.

        Args:
            interaction: The interaction to write.
        """
        date_str = interaction.timestamp.strftime("%Y-%m-%d")
        log_file = self._log_dir / f"{date_str}.jsonl"

        with open(log_file, "a") as f:
            json.dump(interaction.to_dict(), f)
            f.write("\n")

    def read(self, target_date: date) -> list[Interaction]:
        """Read interactions from a daily log file.

        Args:
            target_date: The date to read.

        Returns:
            List of interactions.
        """
        date_str = target_date.strftime("%Y-%m-%d")
        log_file = self._log_dir / f"{date_str}.jsonl"

        if not log_file.exists():
            return []

        interactions = []
        with open(log_file) as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    interactions.append(Interaction.from_dict(data))

        return interactions


class InteractionStorage:
    """Combined storage interface for interactions.

    Writes to both SQLite (for queries) and JSONL (for archival).
    """

    def __init__(self, db_path: Path, log_dir: Path) -> None:
        """Initialize combined storage.

        Args:
            db_path: Path to SQLite database.
            log_dir: Directory for JSONL logs.
        """
        self._sqlite = SQLiteStorage(db_path)
        self._jsonl = JSONLWriter(log_dir)

    @property
    def sqlite(self) -> SQLiteStorage:
        """Get the SQLite storage backend."""
        return self._sqlite

    @property
    def jsonl(self) -> JSONLWriter:
        """Get the JSONL writer backend."""
        return self._jsonl

    def save(self, interaction: Interaction) -> None:
        """Save an interaction to both backends.

        Args:
            interaction: The interaction to save.
        """
        self._sqlite.save(interaction)
        self._jsonl.write(interaction)

    def get_recent(self, limit: int = 10) -> list[Interaction]:
        """Get recent interactions from SQLite.

        Args:
            limit: Maximum number to return.

        Returns:
            List of interactions.
        """
        return self._sqlite.get_recent(limit=limit)

    def close(self) -> None:
        """Close storage connections."""
        self._sqlite.close()


__all__ = [
    "InteractionStorage",
    "JSONLWriter",
    "SQLiteStorage",
]
