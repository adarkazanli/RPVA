"""MongoDB storage client for Ara voice assistant.

Provides connection management, retry logic, and repository access.
"""

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from functools import wraps
from typing import Any, TypeVar

from pymongo import DESCENDING, TEXT, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from .models import InteractionDTO

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_on_connection_failure(
    max_retries: int = 5,
    base_delay: float = 1.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for exponential backoff retry on connection failures.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds (doubles each retry).

    Returns:
        Decorated function with retry logic.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            "Connection failed (attempt %d/%d), retrying in %.1fs: %s",
                            attempt + 1,
                            max_retries,
                            delay,
                            str(e),
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "Connection failed after %d attempts: %s",
                            max_retries,
                            str(e),
                        )

            if last_exception:
                raise last_exception
            raise RuntimeError("Unexpected retry loop exit")

        return wrapper

    return decorator


class InteractionRepository:
    """Repository for interaction storage operations."""

    def __init__(self, collection: Collection[dict[str, Any]]) -> None:
        """Initialize repository with MongoDB collection.

        Args:
            collection: MongoDB collection for interactions.
        """
        self._collection = collection
        self._ensure_indexes()

    def _ensure_indexes(self) -> None:
        """Create indexes for efficient queries."""
        self._collection.create_index([("timestamp", DESCENDING)])
        self._collection.create_index("session_id")
        self._collection.create_index([("device_id", 1), ("timestamp", DESCENDING)])
        self._collection.create_index([("input.transcript", TEXT)])

    @retry_on_connection_failure()
    def save(self, interaction: InteractionDTO) -> str:
        """Save an interaction and return its ID.

        Args:
            interaction: The interaction to save.

        Returns:
            The generated document ID.
        """
        doc = interaction.to_dict()
        doc["created_at"] = datetime.now(UTC)
        result = self._collection.insert_one(doc)
        return str(result.inserted_id)

    @retry_on_connection_failure()
    def get_by_id(self, interaction_id: str) -> InteractionDTO | None:
        """Retrieve an interaction by ID.

        Args:
            interaction_id: The interaction ID.

        Returns:
            The interaction or None if not found.
        """
        from bson import ObjectId

        try:
            doc = self._collection.find_one({"_id": ObjectId(interaction_id)})
        except Exception:
            return None

        if doc is None:
            return None
        return InteractionDTO.from_dict(doc)

    @retry_on_connection_failure()
    def get_by_date_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 100,
    ) -> list[InteractionDTO]:
        """Get interactions within a date range.

        Args:
            start: Start datetime (inclusive).
            end: End datetime (inclusive).
            limit: Maximum number to return.

        Returns:
            List of interactions, most recent first.
        """
        cursor = (
            self._collection.find({"timestamp": {"$gte": start, "$lte": end}})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )

        return [InteractionDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def get_recent(self, limit: int = 10) -> list[InteractionDTO]:
        """Get recent interactions.

        Args:
            limit: Maximum number to return.

        Returns:
            List of interactions, most recent first.
        """
        cursor = self._collection.find().sort("timestamp", DESCENDING).limit(limit)
        return [InteractionDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def search_transcript(self, query: str, limit: int = 20) -> list[InteractionDTO]:
        """Search interactions by transcript text.

        Args:
            query: Search query string.
            limit: Maximum number to return.

        Returns:
            List of matching interactions.
        """
        cursor = (
            self._collection.find({"$text": {"$search": query}})
            .sort("timestamp", DESCENDING)
            .limit(limit)
        )

        return [InteractionDTO.from_dict(doc) for doc in cursor]

    @retry_on_connection_failure()
    def update_events_extracted(self, interaction_id: str, event_ids: list[str]) -> None:
        """Update the events_extracted list for an interaction.

        Args:
            interaction_id: The interaction ID.
            event_ids: List of event IDs to add.
        """
        from bson import ObjectId

        self._collection.update_one(
            {"_id": ObjectId(interaction_id)},
            {"$set": {"events_extracted": event_ids}},
        )


class MongoStorageClient:
    """High-level MongoDB storage client.

    Manages connection and provides access to repositories.
    """

    def __init__(
        self,
        uri: str = "mongodb://localhost:27017",
        database_name: str = "ara",
        max_pool_size: int = 50,
        min_pool_size: int = 10,
        connect_timeout_ms: int = 5000,
        server_selection_timeout_ms: int = 5000,
    ) -> None:
        """Initialize the storage client.

        Args:
            uri: MongoDB connection URI.
            database_name: Name of the database to use.
            max_pool_size: Maximum connection pool size.
            min_pool_size: Minimum connection pool size.
            connect_timeout_ms: Connection timeout in milliseconds.
            server_selection_timeout_ms: Server selection timeout in milliseconds.
        """
        self._uri = uri
        self._database_name = database_name
        self._client: MongoClient[dict[str, Any]] | None = None
        self._db: Database[dict[str, Any]] | None = None
        self._interactions: InteractionRepository | None = None

        self._max_pool_size = max_pool_size
        self._min_pool_size = min_pool_size
        self._connect_timeout_ms = connect_timeout_ms
        self._server_selection_timeout_ms = server_selection_timeout_ms

        self._connected = False

    def connect(self) -> None:
        """Connect to MongoDB.

        Raises:
            ConnectionFailure: If connection fails after retries.
        """
        if self._connected:
            return

        try:
            self._client = MongoClient(
                self._uri,
                maxPoolSize=self._max_pool_size,
                minPoolSize=self._min_pool_size,
                connectTimeoutMS=self._connect_timeout_ms,
                serverSelectionTimeoutMS=self._server_selection_timeout_ms,
            )

            # Verify connection
            self._client.admin.command("ping")

            self._db = self._client[self._database_name]
            self._interactions = InteractionRepository(self._db["interactions"])
            self._connected = True

            logger.info("Connected to MongoDB at %s", self._uri)

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error("Failed to connect to MongoDB: %s", str(e))
            self._connected = False
            raise

    def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            self._interactions = None
            self._connected = False
            logger.info("Disconnected from MongoDB")

    def is_connected(self) -> bool:
        """Check if connected to MongoDB.

        Returns:
            True if connected, False otherwise.
        """
        if not self._connected or self._client is None:
            return False

        try:
            self._client.admin.command("ping")
            return True
        except Exception:
            self._connected = False
            return False

    def health_check(self) -> bool:
        """Perform a health check on the database.

        Returns:
            True if healthy, False otherwise.
        """
        return self.is_connected()

    @property
    def interactions(self) -> InteractionRepository:
        """Get the interactions repository.

        Returns:
            The InteractionRepository instance.

        Raises:
            RuntimeError: If not connected.
        """
        if self._interactions is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        return self._interactions

    @property
    def database(self) -> Database[dict[str, Any]]:
        """Get the database instance.

        Returns:
            The MongoDB database.

        Raises:
            RuntimeError: If not connected.
        """
        if self._db is None:
            raise RuntimeError("Not connected to MongoDB. Call connect() first.")
        return self._db

    def __enter__(self) -> "MongoStorageClient":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.disconnect()


__all__ = [
    "MongoStorageClient",
    "InteractionRepository",
    "retry_on_connection_failure",
]
