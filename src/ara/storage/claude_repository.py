"""MongoDB repository for Claude queries and responses.

Provides persistence layer for Claude conversation history.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pymongo.collection import Collection
    from pymongo.database import Database


class ClaudeRepository:
    """Repository for Claude query storage."""

    COLLECTION_NAME = "claude_queries"
    TYPE_QUERY = "claude_query"
    TYPE_RESPONSE = "claude_response"

    def __init__(self, database: Database) -> None:
        """Initialize repository with database connection.

        Args:
            database: MongoDB database instance.
        """
        self._db = database
        self._collection: Collection = database[self.COLLECTION_NAME]
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create indexes for efficient querying."""
        self._collection.create_index([("timestamp", -1)])
        self._collection.create_index("session_id")
        self._collection.create_index("type")
        self._collection.create_index("query_id")

    def save_query(
        self,
        session_id: str,
        utterance: str,
        is_followup: bool,
        timestamp: datetime,
    ) -> str:
        """Save a Claude query.

        Args:
            session_id: Session UUID.
            utterance: Original user speech.
            is_followup: Whether query was in follow-up window.
            timestamp: When query was received.

        Returns:
            Document ID of saved query.
        """
        doc_id = str(uuid.uuid4())
        document = {
            "_id": doc_id,
            "type": self.TYPE_QUERY,
            "session_id": session_id,
            "utterance": utterance,
            "is_followup": is_followup,
            "timestamp": timestamp,
        }
        self._collection.insert_one(document)
        return doc_id

    def save_response(
        self,
        query_id: str,
        session_id: str,
        text: str,
        tokens_used: int,
        model: str,
        latency_ms: int,
        timestamp: datetime,
    ) -> str:
        """Save a Claude response.

        Args:
            query_id: Reference to the query.
            session_id: Session UUID.
            text: Response text from Claude.
            tokens_used: Total tokens consumed.
            model: Claude model used.
            latency_ms: API response time.
            timestamp: When response was received.

        Returns:
            Document ID of saved response.
        """
        doc_id = str(uuid.uuid4())
        document = {
            "_id": doc_id,
            "type": self.TYPE_RESPONSE,
            "query_id": query_id,
            "session_id": session_id,
            "text": text,
            "tokens_used": tokens_used,
            "model": model,
            "latency_ms": latency_ms,
            "timestamp": timestamp,
        }
        self._collection.insert_one(document)
        return doc_id

    def get_queries_by_date_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 100,
    ) -> list[dict]:
        """Get queries within a date range.

        Args:
            start: Start datetime (inclusive).
            end: End datetime (inclusive).
            limit: Maximum results to return.

        Returns:
            List of query documents, most recent first.
        """
        cursor = self._collection.find(
            {
                "type": self.TYPE_QUERY,
                "timestamp": {"$gte": start, "$lte": end},
            }
        ).sort("timestamp", -1).limit(limit)
        return list(cursor)

    def get_response_for_query(self, query_id: str) -> dict | None:
        """Get response for a specific query.

        Args:
            query_id: Query document ID.

        Returns:
            Response document or None if not found.
        """
        return self._collection.find_one(
            {
                "type": self.TYPE_RESPONSE,
                "query_id": query_id,
            }
        )

    def get_conversations_for_period(
        self,
        start: datetime,
        end: datetime,
    ) -> list[tuple[dict, dict | None]]:
        """Get query-response pairs for a time period.

        Args:
            start: Start datetime.
            end: End datetime.

        Returns:
            List of (query, response) tuples for summarization.
        """
        queries = self.get_queries_by_date_range(start, end)
        conversations = []
        for query in queries:
            response = self.get_response_for_query(query["_id"])
            conversations.append((query, response))
        return conversations


__all__ = ["ClaudeRepository"]
