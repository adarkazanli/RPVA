"""Integration tests for time query flow.

Tests end-to-end duration and time-based queries.
"""

import time
from datetime import UTC, datetime, timedelta

import pytest

from ara.storage.client import MongoStorageClient
from ara.storage.events import ActivityRepository, EventRepository
from ara.storage.models import ActivityDTO, ActivityStatus, EventDTO, EventType


@pytest.fixture
def mongo_client() -> MongoStorageClient:
    """Create MongoDB client for testing."""
    client = MongoStorageClient(
        uri="mongodb://localhost:27017",
        database_name="ara_test_queries",
        connect_timeout_ms=2000,
        server_selection_timeout_ms=2000,
    )
    try:
        client.connect()
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")

    yield client

    # Cleanup
    if client.is_connected():
        client.database.client.drop_database("ara_test_queries")
    client.disconnect()


@pytest.fixture
def event_repo(mongo_client: MongoStorageClient) -> EventRepository:
    """Create EventRepository for testing."""
    return EventRepository(mongo_client.database["events"])


@pytest.fixture
def activity_repo(mongo_client: MongoStorageClient) -> ActivityRepository:
    """Create ActivityRepository for testing."""
    return ActivityRepository(mongo_client.database["activities"])


@pytest.fixture
def storage_facade(
    mongo_client: MongoStorageClient,
    event_repo: EventRepository,
    activity_repo: ActivityRepository,
) -> "MockStorageFacade":
    """Create a storage facade for TimeQueryHandler."""

    class MockStorageFacade:
        def __init__(
            self, events: EventRepository, activities: ActivityRepository
        ) -> None:
            self.events = events
            self.activities = activities

    return MockStorageFacade(event_repo, activity_repo)


@pytest.fixture
def seeded_shower_activity(
    event_repo: EventRepository, activity_repo: ActivityRepository
) -> ActivityDTO:
    """Seed a completed shower activity for testing."""
    start_time = datetime.now(UTC) - timedelta(hours=2)
    end_time = start_time + timedelta(minutes=15)

    # Create start event
    start_event_id = event_repo.save(
        EventDTO(
            interaction_id="int-1",
            timestamp=start_time,
            event_type=EventType.ACTIVITY_START,
            context="shower",
            source_text="I'm taking a shower",
            extraction_confidence=0.9,
        )
    )

    # Create end event
    end_event_id = event_repo.save(
        EventDTO(
            interaction_id="int-2",
            timestamp=end_time,
            event_type=EventType.ACTIVITY_END,
            context="shower",
            source_text="done with my shower",
            extraction_confidence=0.9,
        )
    )

    # Link events
    event_repo.link_events(start_event_id, end_event_id)

    # Create activity
    activity = ActivityDTO(
        name="shower",
        status=ActivityStatus.COMPLETED,
        start_event_id=start_event_id,
        end_event_id=end_event_id,
        start_time=start_time,
        end_time=end_time,
        duration_ms=15 * 60 * 1000,  # 15 minutes
        start_text="I'm taking a shower",
        end_text="done with my shower",
        pairing_score=0.95,
    )
    activity_id = activity_repo.save(activity)

    # Return saved activity
    return activity_repo.get_by_id(activity_id)  # type: ignore


@pytest.mark.integration
class TestDurationQueryFlow:
    """Integration tests for duration query flow."""

    def test_how_long_was_i_in_the_shower(
        self, storage_facade: "MockStorageFacade", seeded_shower_activity: ActivityDTO
    ) -> None:
        """Test 'How long was I in the shower?' query."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(storage_facade)

        result = handler.query_duration("shower")

        assert result.success is True
        assert result.duration_ms == 15 * 60 * 1000
        assert "15 minutes" in result.response_text

    def test_duration_query_within_2_seconds(
        self,
        storage_facade: "MockStorageFacade",
        seeded_shower_activity: ActivityDTO,
    ) -> None:
        """Test that duration query responds within 2 seconds (SC-001)."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(storage_facade)

        start = time.perf_counter()
        result = handler.query_duration("shower")
        elapsed = time.perf_counter() - start

        assert result.success is True
        assert elapsed < 2.0, f"Query took {elapsed:.2f}s, should be < 2s"

    def test_duration_query_not_found(
        self, storage_facade: "MockStorageFacade"
    ) -> None:
        """Test duration query when activity not found."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(storage_facade)

        result = handler.query_duration("yoga")

        assert result.success is False
        assert "couldn't find" in result.response_text.lower()


@pytest.mark.integration
class TestAroundTimeQueryFlow:
    """Integration tests for around-time query flow."""

    def test_what_was_i_doing_around_time(
        self,
        storage_facade: "MockStorageFacade",
        seeded_shower_activity: ActivityDTO,
    ) -> None:
        """Test 'What was I doing around [time]?' query."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(storage_facade)

        # Query around the time the shower was happening
        time_point = datetime.now(UTC) - timedelta(hours=2, minutes=5)
        result = handler.query_around_time(time_point, window_minutes=30)

        assert result.success is True
        assert len(result.events_found) > 0

    def test_around_time_query_within_2_seconds(
        self,
        storage_facade: "MockStorageFacade",
        seeded_shower_activity: ActivityDTO,
    ) -> None:
        """Test that around-time query responds within 2 seconds (SC-002)."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(storage_facade)
        time_point = datetime.now(UTC) - timedelta(hours=2)

        start = time.perf_counter()
        result = handler.query_around_time(time_point)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"Query took {elapsed:.2f}s, should be < 2s"


@pytest.mark.integration
class TestRangeQueryFlow:
    """Integration tests for range query flow."""

    def test_what_happened_between(
        self, storage_facade: "MockStorageFacade", event_repo: EventRepository
    ) -> None:
        """Test 'What happened between X and Y?' query."""
        from ara.storage.queries import TimeQueryHandler

        # Seed events in range
        base_time = datetime.now(UTC) - timedelta(hours=4)
        event_repo.save(
            EventDTO(
                interaction_id="int-1",
                timestamp=base_time + timedelta(minutes=30),
                event_type=EventType.NOTE,
                context="meeting",
                source_text="starting meeting",
                extraction_confidence=0.9,
            )
        )
        event_repo.save(
            EventDTO(
                interaction_id="int-2",
                timestamp=base_time + timedelta(hours=1),
                event_type=EventType.NOTE,
                context="lunch",
                source_text="going to lunch",
                extraction_confidence=0.9,
            )
        )

        handler = TimeQueryHandler(storage_facade)

        start = base_time
        end = base_time + timedelta(hours=2)
        result = handler.query_range(start, end)

        assert result.success is True
        assert len(result.events_found) == 2
