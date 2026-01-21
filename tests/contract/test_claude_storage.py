"""Contract tests for Claude storage repository.

Tests the MongoDB repository contract for Claude queries and responses.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from mongomock import MongoClient

from ara.storage.claude_repository import ClaudeRepository


@pytest.fixture
def mock_db():
    """Create a mock MongoDB database for testing."""
    client = MongoClient()
    return client["ara_test"]


@pytest.fixture
def repository(mock_db) -> ClaudeRepository:
    """Create ClaudeRepository with mock database."""
    return ClaudeRepository(mock_db)


class TestClaudeRepositorySaveQuery:
    """Contract tests for ClaudeRepository.save_query()."""

    def test_save_query_returns_document_id(self, repository: ClaudeRepository) -> None:
        """Test that save_query returns a valid document ID."""
        session_id = str(uuid.uuid4())
        doc_id = repository.save_query(
            session_id=session_id,
            utterance="what is the capital of France",
            is_followup=False,
            timestamp=datetime.now(UTC),
        )
        assert doc_id is not None
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0

    def test_save_query_stores_all_fields(self, repository: ClaudeRepository) -> None:
        """Test that save_query persists all required fields."""
        session_id = str(uuid.uuid4())
        utterance = "explain quantum computing"
        # Use datetime with second precision to avoid microsecond truncation issues
        timestamp = datetime(2024, 1, 15, 10, 30, 0)

        doc_id = repository.save_query(
            session_id=session_id,
            utterance=utterance,
            is_followup=True,
            timestamp=timestamp,
        )

        # Retrieve and verify
        doc = repository._collection.find_one({"_id": doc_id})
        assert doc is not None
        assert doc["session_id"] == session_id
        assert doc["utterance"] == utterance
        assert doc["is_followup"] is True
        assert doc["timestamp"] == timestamp

    def test_save_query_sets_type_field(self, repository: ClaudeRepository) -> None:
        """Test that save_query sets type='claude_query'."""
        session_id = str(uuid.uuid4())
        doc_id = repository.save_query(
            session_id=session_id,
            utterance="test query",
            is_followup=False,
            timestamp=datetime.now(UTC),
        )

        doc = repository._collection.find_one({"_id": doc_id})
        assert doc["type"] == "claude_query"


class TestClaudeRepositorySaveResponse:
    """Contract tests for ClaudeRepository.save_response()."""

    def test_save_response_returns_document_id(
        self, repository: ClaudeRepository
    ) -> None:
        """Test that save_response returns a valid document ID."""
        session_id = str(uuid.uuid4())
        query_id = str(uuid.uuid4())

        doc_id = repository.save_response(
            query_id=query_id,
            session_id=session_id,
            text="Paris is the capital of France.",
            tokens_used=50,
            model="claude-sonnet-4-20250514",
            latency_ms=1500,
            timestamp=datetime.now(UTC),
        )
        assert doc_id is not None
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0

    def test_save_response_links_to_query(self, repository: ClaudeRepository) -> None:
        """Test that save_response correctly references the query."""
        session_id = str(uuid.uuid4())
        query_id = "test-query-123"

        doc_id = repository.save_response(
            query_id=query_id,
            session_id=session_id,
            text="Response text",
            tokens_used=30,
            model="claude-sonnet-4-20250514",
            latency_ms=1000,
            timestamp=datetime.now(UTC),
        )

        doc = repository._collection.find_one({"_id": doc_id})
        assert doc["query_id"] == query_id

    def test_save_response_sets_type_field(self, repository: ClaudeRepository) -> None:
        """Test that save_response sets type='claude_response'."""
        session_id = str(uuid.uuid4())
        doc_id = repository.save_response(
            query_id="test-query",
            session_id=session_id,
            text="Response text",
            tokens_used=30,
            model="claude-sonnet-4-20250514",
            latency_ms=1000,
            timestamp=datetime.now(UTC),
        )

        doc = repository._collection.find_one({"_id": doc_id})
        assert doc["type"] == "claude_response"


class TestClaudeRepositoryDateRangeQueries:
    """Contract tests for time-based query retrieval."""

    def test_get_queries_by_date_range_filters_correctly(
        self, repository: ClaudeRepository
    ) -> None:
        """Test that date range filtering works correctly."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        # Create queries at different times
        old_time = now - timedelta(days=2)
        recent_time = now - timedelta(hours=1)
        future_time = now + timedelta(days=1)

        # Save queries at different times
        repository.save_query(
            session_id=session_id,
            utterance="old query",
            is_followup=False,
            timestamp=old_time,
        )
        repository.save_query(
            session_id=session_id,
            utterance="recent query",
            is_followup=False,
            timestamp=recent_time,
        )
        repository.save_query(
            session_id=session_id,
            utterance="future query",
            is_followup=False,
            timestamp=future_time,
        )

        # Query for last 24 hours
        start = now - timedelta(days=1)
        end = now
        results = repository.get_queries_by_date_range(start, end)

        # Should only include recent query
        assert len(results) == 1
        assert results[0]["utterance"] == "recent query"

    def test_get_queries_by_date_range_respects_limit(
        self, repository: ClaudeRepository
    ) -> None:
        """Test that limit parameter is respected."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        # Create multiple queries
        for i in range(5):
            repository.save_query(
                session_id=session_id,
                utterance=f"query {i}",
                is_followup=False,
                timestamp=now - timedelta(minutes=i),
            )

        # Query with limit
        start = now - timedelta(days=1)
        end = now + timedelta(hours=1)
        results = repository.get_queries_by_date_range(start, end, limit=3)

        assert len(results) == 3

    def test_get_queries_by_date_range_returns_most_recent_first(
        self, repository: ClaudeRepository
    ) -> None:
        """Test that results are sorted by timestamp descending."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        # Create queries in random order
        times = [
            now - timedelta(minutes=30),
            now - timedelta(minutes=10),
            now - timedelta(minutes=20),
        ]
        for i, t in enumerate(times):
            repository.save_query(
                session_id=session_id,
                utterance=f"query {i}",
                is_followup=False,
                timestamp=t,
            )

        start = now - timedelta(hours=1)
        end = now
        results = repository.get_queries_by_date_range(start, end)

        # Most recent first (10min ago, 20min ago, 30min ago)
        assert len(results) == 3
        assert results[0]["utterance"] == "query 1"  # 10 min ago
        assert results[1]["utterance"] == "query 2"  # 20 min ago
        assert results[2]["utterance"] == "query 0"  # 30 min ago

    def test_get_response_for_query_returns_matching_response(
        self, repository: ClaudeRepository
    ) -> None:
        """Test that get_response_for_query finds the correct response."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        # Save query and response
        query_id = repository.save_query(
            session_id=session_id,
            utterance="test question",
            is_followup=False,
            timestamp=now,
        )
        repository.save_response(
            query_id=query_id,
            session_id=session_id,
            text="test answer",
            tokens_used=50,
            model="claude-sonnet-4-20250514",
            latency_ms=1000,
            timestamp=now,
        )

        response = repository.get_response_for_query(query_id)
        assert response is not None
        assert response["text"] == "test answer"
        assert response["query_id"] == query_id

    def test_get_response_for_query_returns_none_when_not_found(
        self, repository: ClaudeRepository
    ) -> None:
        """Test that get_response_for_query returns None for missing query."""
        response = repository.get_response_for_query("nonexistent-query-id")
        assert response is None

    def test_get_conversations_for_period_returns_pairs(
        self, repository: ClaudeRepository
    ) -> None:
        """Test that conversation pairs are returned correctly."""
        session_id = str(uuid.uuid4())
        now = datetime.now(UTC)

        # Create query with response
        query_id_1 = repository.save_query(
            session_id=session_id,
            utterance="question 1",
            is_followup=False,
            timestamp=now - timedelta(minutes=10),
        )
        repository.save_response(
            query_id=query_id_1,
            session_id=session_id,
            text="answer 1",
            tokens_used=50,
            model="claude-sonnet-4-20250514",
            latency_ms=1000,
            timestamp=now - timedelta(minutes=10),
        )

        # Create query without response (user interrupted)
        repository.save_query(
            session_id=session_id,
            utterance="question 2",
            is_followup=False,
            timestamp=now - timedelta(minutes=5),
        )

        start = now - timedelta(hours=1)
        end = now
        conversations = repository.get_conversations_for_period(start, end)

        # Should have 2 conversations
        assert len(conversations) == 2

        # First one (most recent) has no response
        query, response = conversations[0]
        assert query["utterance"] == "question 2"
        assert response is None

        # Second one has response
        query, response = conversations[1]
        assert query["utterance"] == "question 1"
        assert response is not None
        assert response["text"] == "answer 1"
