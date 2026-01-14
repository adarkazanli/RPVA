"""Integration tests for MongoDB storage.

Tests require MongoDB running in Docker container.
Run: docker-compose -f docker/docker-compose.yml up -d
"""

from datetime import UTC, datetime, timedelta

import pytest

from ara.storage.client import MongoStorageClient
from ara.storage.events import ActivityRepository, EventRepository
from ara.storage.models import (
    ActivityDTO,
    ActivityStatus,
    EventDTO,
    EventType,
    InteractionDTO,
)


@pytest.fixture
def mongo_client() -> MongoStorageClient:
    """Create a MongoDB client for testing.

    Uses a test database that is cleaned up after each test.
    """
    client = MongoStorageClient(
        uri="mongodb://localhost:27017",
        database_name="ara_test",
        connect_timeout_ms=2000,
        server_selection_timeout_ms=2000,
    )
    try:
        client.connect()
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")

    yield client

    # Cleanup: drop test database
    if client.is_connected():
        client.database.client.drop_database("ara_test")
    client.disconnect()


@pytest.fixture
def event_repo(mongo_client: MongoStorageClient) -> EventRepository:
    """Create an EventRepository for testing."""
    return EventRepository(mongo_client.database["events"])


@pytest.fixture
def activity_repo(mongo_client: MongoStorageClient) -> ActivityRepository:
    """Create an ActivityRepository for testing."""
    return ActivityRepository(mongo_client.database["activities"])


@pytest.mark.integration
class TestMongoDBConnection:
    """Integration tests for MongoDB connection."""

    def test_connect_and_ping(self, mongo_client: MongoStorageClient) -> None:
        """Test connecting to MongoDB and pinging."""
        assert mongo_client.is_connected()
        assert mongo_client.health_check()

    def test_reconnect_after_disconnect(self, mongo_client: MongoStorageClient) -> None:
        """Test reconnecting after disconnect."""
        mongo_client.disconnect()
        assert not mongo_client.is_connected()

        mongo_client.connect()
        assert mongo_client.is_connected()


@pytest.mark.integration
class TestInteractionRepository:
    """Integration tests for InteractionRepository CRUD operations."""

    def test_save_and_retrieve_interaction(
        self, mongo_client: MongoStorageClient
    ) -> None:
        """Test saving and retrieving an interaction."""
        interaction = InteractionDTO(
            session_id="test-session-001",
            timestamp=datetime.now(UTC),
            device_id="test-device",
            transcript="what time is it",
            transcript_confidence=0.95,
            intent_type="time_query",
            intent_confidence=0.9,
            response_text="It is 10:30 AM",
            response_source="local",
            latency_ms={"total": 150},
        )

        interaction_id = mongo_client.interactions.save(interaction)
        assert interaction_id is not None

        retrieved = mongo_client.interactions.get_by_id(interaction_id)
        assert retrieved is not None
        assert retrieved.transcript == "what time is it"
        assert retrieved.intent_type == "time_query"

    def test_get_recent_interactions(self, mongo_client: MongoStorageClient) -> None:
        """Test retrieving recent interactions."""
        base_time = datetime.now(UTC)

        # Save multiple interactions
        for i in range(5):
            interaction = InteractionDTO(
                session_id=f"session-{i}",
                timestamp=base_time - timedelta(minutes=i),
                device_id="test-device",
                transcript=f"test query {i}",
                transcript_confidence=0.9,
                intent_type="general_question",
                intent_confidence=0.8,
                response_text=f"response {i}",
                response_source="local",
                latency_ms={"total": 100},
            )
            mongo_client.interactions.save(interaction)

        recent = mongo_client.interactions.get_recent(limit=3)
        assert len(recent) == 3
        # Most recent should be first
        assert recent[0].transcript == "test query 0"

    def test_get_by_date_range(self, mongo_client: MongoStorageClient) -> None:
        """Test retrieving interactions by date range."""
        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)

        # Save interaction from today
        today_interaction = InteractionDTO(
            session_id="today-session",
            timestamp=now,
            device_id="test-device",
            transcript="today query",
            transcript_confidence=0.9,
            intent_type="general_question",
            intent_confidence=0.8,
            response_text="today response",
            response_source="local",
            latency_ms={"total": 100},
        )
        mongo_client.interactions.save(today_interaction)

        # Save interaction from yesterday
        yesterday_interaction = InteractionDTO(
            session_id="yesterday-session",
            timestamp=yesterday,
            device_id="test-device",
            transcript="yesterday query",
            transcript_confidence=0.9,
            intent_type="general_question",
            intent_confidence=0.8,
            response_text="yesterday response",
            response_source="local",
            latency_ms={"total": 100},
        )
        mongo_client.interactions.save(yesterday_interaction)

        # Query for today only
        results = mongo_client.interactions.get_by_date_range(
            start=now - timedelta(hours=1),
            end=now + timedelta(hours=1),
        )
        assert len(results) == 1
        assert results[0].transcript == "today query"

        # Query for both days
        results = mongo_client.interactions.get_by_date_range(
            start=two_days_ago,
            end=now + timedelta(hours=1),
        )
        assert len(results) == 2


@pytest.mark.integration
class TestEventRepository:
    """Integration tests for EventRepository."""

    def test_save_and_retrieve_event(self, event_repo: EventRepository) -> None:
        """Test saving and retrieving an event."""
        event = EventDTO(
            interaction_id="interaction-123",
            timestamp=datetime.now(UTC),
            event_type=EventType.ACTIVITY_START,
            context="gym",
            source_text="I'm going to the gym",
            extraction_confidence=0.9,
        )

        event_id = event_repo.save(event)
        assert event_id is not None

        retrieved = event_repo.get_by_id(event_id)
        assert retrieved is not None
        assert retrieved.context == "gym"
        assert retrieved.event_type == EventType.ACTIVITY_START

    def test_get_by_type(self, event_repo: EventRepository) -> None:
        """Test retrieving events by type."""
        # Save different event types
        event_repo.save(
            EventDTO(
                interaction_id="int-1",
                timestamp=datetime.now(UTC),
                event_type=EventType.ACTIVITY_START,
                context="gym",
                source_text="going to gym",
                extraction_confidence=0.9,
            )
        )
        event_repo.save(
            EventDTO(
                interaction_id="int-2",
                timestamp=datetime.now(UTC),
                event_type=EventType.NOTE,
                context="buy milk",
                source_text="note: buy milk",
                extraction_confidence=0.85,
            )
        )

        start_events = event_repo.get_by_type(EventType.ACTIVITY_START)
        assert len(start_events) == 1
        assert start_events[0].context == "gym"

        note_events = event_repo.get_by_type(EventType.NOTE)
        assert len(note_events) == 1
        assert note_events[0].context == "buy milk"

    def test_get_around_time(self, event_repo: EventRepository) -> None:
        """Test retrieving events around a time point."""
        now = datetime.now(UTC)

        # Event 10 minutes ago
        event_repo.save(
            EventDTO(
                interaction_id="int-1",
                timestamp=now - timedelta(minutes=10),
                event_type=EventType.ACTIVITY_START,
                context="shower",
                source_text="taking a shower",
                extraction_confidence=0.9,
            )
        )

        # Event 2 hours ago (outside window)
        event_repo.save(
            EventDTO(
                interaction_id="int-2",
                timestamp=now - timedelta(hours=2),
                event_type=EventType.NOTE,
                context="old note",
                source_text="old note",
                extraction_confidence=0.9,
            )
        )

        events = event_repo.get_around_time(now, window_minutes=30)
        assert len(events) == 1
        assert events[0].context == "shower"

    def test_link_events(self, event_repo: EventRepository) -> None:
        """Test linking start and end events."""
        start_id = event_repo.save(
            EventDTO(
                interaction_id="int-1",
                timestamp=datetime.now(UTC),
                event_type=EventType.ACTIVITY_START,
                context="gym",
                source_text="going to gym",
                extraction_confidence=0.9,
            )
        )

        end_id = event_repo.save(
            EventDTO(
                interaction_id="int-2",
                timestamp=datetime.now(UTC) + timedelta(hours=1),
                event_type=EventType.ACTIVITY_END,
                context="gym",
                source_text="back from gym",
                extraction_confidence=0.9,
            )
        )

        event_repo.link_events(start_id, end_id)

        start_event = event_repo.get_by_id(start_id)
        end_event = event_repo.get_by_id(end_id)

        assert start_event is not None
        assert start_event.linked_event_id == end_id
        assert end_event is not None
        assert end_event.linked_event_id == start_id


@pytest.mark.integration
class TestActivityRepository:
    """Integration tests for ActivityRepository."""

    def test_save_and_complete_activity(
        self, activity_repo: ActivityRepository, event_repo: EventRepository
    ) -> None:
        """Test saving an activity and completing it."""
        start_time = datetime.now(UTC)
        end_time = start_time + timedelta(minutes=45)

        # Create start event
        start_event_id = event_repo.save(
            EventDTO(
                interaction_id="int-1",
                timestamp=start_time,
                event_type=EventType.ACTIVITY_START,
                context="workout",
                source_text="starting workout",
                extraction_confidence=0.9,
            )
        )

        # Create activity
        activity = ActivityDTO(
            name="workout",
            status=ActivityStatus.IN_PROGRESS,
            start_event_id=start_event_id,
            start_time=start_time,
            start_text="starting workout",
            pairing_score=1.0,
        )
        activity_id = activity_repo.save(activity)

        # Verify in progress
        in_progress = activity_repo.get_in_progress()
        assert len(in_progress) == 1
        assert in_progress[0].name == "workout"

        # Create end event
        end_event_id = event_repo.save(
            EventDTO(
                interaction_id="int-2",
                timestamp=end_time,
                event_type=EventType.ACTIVITY_END,
                context="workout",
                source_text="finished workout",
                extraction_confidence=0.9,
            )
        )

        # Complete activity
        completed = activity_repo.complete(
            activity_id=activity_id,
            end_event_id=end_event_id,
            end_time=end_time,
            end_text="finished workout",
        )

        assert completed is not None
        assert completed.status == ActivityStatus.COMPLETED
        assert completed.duration_ms == 45 * 60 * 1000  # 45 minutes in ms

        # Verify no longer in progress
        in_progress = activity_repo.get_in_progress()
        assert len(in_progress) == 0

    def test_get_by_name(self, activity_repo: ActivityRepository) -> None:
        """Test searching activities by name."""
        activity_repo.save(
            ActivityDTO(
                name="gym session",
                status=ActivityStatus.COMPLETED,
                start_event_id="event-1",
                start_time=datetime.now(UTC),
                start_text="going to gym",
                pairing_score=0.9,
            )
        )
        activity_repo.save(
            ActivityDTO(
                name="shower",
                status=ActivityStatus.COMPLETED,
                start_event_id="event-2",
                start_time=datetime.now(UTC),
                start_text="taking shower",
                pairing_score=0.9,
            )
        )

        gym_activities = activity_repo.get_by_name("gym")
        assert len(gym_activities) == 1
        assert gym_activities[0].name == "gym session"

    def test_calculate_average_duration(
        self, activity_repo: ActivityRepository
    ) -> None:
        """Test calculating average duration for an activity type."""
        base_time = datetime.now(UTC)

        # Save completed activities with durations
        activity_repo.save(
            ActivityDTO(
                name="shower",
                status=ActivityStatus.COMPLETED,
                start_event_id="event-1",
                start_time=base_time,
                start_text="taking shower",
                pairing_score=0.9,
                duration_ms=600000,  # 10 minutes
            )
        )
        activity_repo.save(
            ActivityDTO(
                name="shower",
                status=ActivityStatus.COMPLETED,
                start_event_id="event-2",
                start_time=base_time - timedelta(days=1),
                start_text="taking shower",
                pairing_score=0.9,
                duration_ms=900000,  # 15 minutes
            )
        )

        avg = activity_repo.calculate_average_duration("shower")
        assert avg is not None
        assert avg == 750000  # Average of 10 and 15 minutes = 12.5 minutes


@pytest.mark.integration
class TestQueryLatency:
    """Integration tests for query latency requirements."""

    def test_recent_query_under_500ms(self, mongo_client: MongoStorageClient) -> None:
        """Test that recent query completes under 500ms (NFR requirement)."""
        import time

        # Save some interactions
        for i in range(100):
            interaction = InteractionDTO(
                session_id=f"session-{i}",
                timestamp=datetime.now(UTC) - timedelta(minutes=i),
                device_id="test-device",
                transcript=f"test query {i}",
                transcript_confidence=0.9,
                intent_type="general_question",
                intent_confidence=0.8,
                response_text=f"response {i}",
                response_source="local",
                latency_ms={"total": 100},
            )
            mongo_client.interactions.save(interaction)

        # Measure query time
        start = time.perf_counter()
        results = mongo_client.interactions.get_recent(limit=10)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert len(results) == 10
        assert elapsed_ms < 500, f"Query took {elapsed_ms:.0f}ms, should be < 500ms"
