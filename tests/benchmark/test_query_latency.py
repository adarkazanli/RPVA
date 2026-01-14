"""Benchmark tests for query latency.

Verifies query performance meets <2s target (SC-001, SC-002).
"""

import time
from datetime import UTC, datetime, timedelta

import pytest

from ara.storage.client import MongoStorageClient
from ara.storage.events import ActivityRepository, EventRepository
from ara.storage.models import ActivityDTO, ActivityStatus, EventDTO, EventType


@pytest.fixture
def mongo_client() -> MongoStorageClient:
    """Create MongoDB client for benchmarking."""
    client = MongoStorageClient(
        uri="mongodb://localhost:27017",
        database_name="ara_benchmark",
        connect_timeout_ms=2000,
        server_selection_timeout_ms=2000,
    )
    try:
        client.connect()
    except Exception as e:
        pytest.skip(f"MongoDB not available: {e}")

    yield client

    if client.is_connected():
        client.database.client.drop_database("ara_benchmark")
    client.disconnect()


@pytest.fixture
def event_repo(mongo_client: MongoStorageClient) -> EventRepository:
    """Create EventRepository for benchmarking."""
    return EventRepository(mongo_client.database["events"])


@pytest.fixture
def activity_repo(mongo_client: MongoStorageClient) -> ActivityRepository:
    """Create ActivityRepository for benchmarking."""
    return ActivityRepository(mongo_client.database["activities"])


@pytest.fixture
def storage_facade(
    event_repo: EventRepository, activity_repo: ActivityRepository
) -> "BenchmarkStorage":
    """Create storage facade for TimeQueryHandler."""

    class BenchmarkStorage:
        def __init__(self, events: EventRepository, activities: ActivityRepository):
            self.events = events
            self.activities = activities

    return BenchmarkStorage(event_repo, activity_repo)


@pytest.fixture
def seeded_data(
    event_repo: EventRepository, activity_repo: ActivityRepository
) -> dict[str, int]:
    """Seed test data for benchmarking.

    Creates events and activities for 30 days with varying volumes.
    Returns counts of created items.
    """
    base_time = datetime.now(UTC)
    event_count = 0
    activity_count = 0

    # Create data for past 30 days
    for day_offset in range(30):
        day_start = base_time - timedelta(days=day_offset)

        # Create 10 events per day
        for hour in range(10):
            event_time = day_start.replace(hour=8 + hour, minute=0, second=0)

            event_repo.save(
                EventDTO(
                    interaction_id=f"int-{day_offset}-{hour}",
                    timestamp=event_time,
                    event_type=EventType.NOTE,
                    context=f"event_{day_offset}_{hour}",
                    source_text=f"event on day {day_offset} hour {hour}",
                    extraction_confidence=0.9,
                )
            )
            event_count += 1

        # Create 2 activities per day
        for i in range(2):
            activity_repo.save(
                ActivityDTO(
                    name=f"activity_{day_offset}_{i}",
                    status=ActivityStatus.COMPLETED,
                    start_event_id=f"event-start-{day_offset}-{i}",
                    start_time=day_start.replace(hour=9 + i * 4, minute=0),
                    start_text=f"started activity {i}",
                    pairing_score=0.9,
                    duration_ms=(30 + i * 15) * 60 * 1000,  # 30 or 45 minutes
                )
            )
            activity_count += 1

    return {"events": event_count, "activities": activity_count}


@pytest.mark.benchmark
class TestDurationQueryLatency:
    """Benchmark tests for duration query performance (SC-001)."""

    def test_duration_query_under_2_seconds(
        self, storage_facade: "BenchmarkStorage", seeded_data: dict[str, int]
    ) -> None:
        """Test duration query completes under 2 seconds with 30 days of data."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(storage_facade)

        # Warm up
        handler.query_duration("activity_0_0")

        # Measure
        start = time.perf_counter()
        result = handler.query_duration("activity_0_0")
        elapsed = time.perf_counter() - start

        assert result.success is True
        assert elapsed < 2.0, f"Duration query took {elapsed:.3f}s, should be < 2s"

    def test_duration_query_with_10_events(
        self, activity_repo: ActivityRepository
    ) -> None:
        """Test duration query latency with 10 activities."""
        from ara.storage.queries import TimeQueryHandler

        class MinimalStorage:
            def __init__(self, activities: ActivityRepository):
                self.activities = activities
                self.events = None

        # Seed 10 activities
        for i in range(10):
            activity_repo.save(
                ActivityDTO(
                    name="shower",
                    status=ActivityStatus.COMPLETED,
                    start_event_id=f"event-{i}",
                    start_time=datetime.now(UTC) - timedelta(days=i),
                    start_text="taking shower",
                    pairing_score=0.9,
                    duration_ms=15 * 60 * 1000,
                )
            )

        storage = MinimalStorage(activity_repo)
        handler = TimeQueryHandler(storage)  # type: ignore

        start = time.perf_counter()
        result = handler.query_duration("shower")
        elapsed = time.perf_counter() - start

        assert result.success is True
        assert elapsed < 2.0

    def test_duration_query_with_100_events(
        self, activity_repo: ActivityRepository
    ) -> None:
        """Test duration query latency with 100 activities."""
        from ara.storage.queries import TimeQueryHandler

        class MinimalStorage:
            def __init__(self, activities: ActivityRepository):
                self.activities = activities
                self.events = None

        # Seed 100 activities
        for i in range(100):
            activity_repo.save(
                ActivityDTO(
                    name="shower",
                    status=ActivityStatus.COMPLETED,
                    start_event_id=f"event-{i}",
                    start_time=datetime.now(UTC) - timedelta(hours=i),
                    start_text="taking shower",
                    pairing_score=0.9,
                    duration_ms=15 * 60 * 1000,
                )
            )

        storage = MinimalStorage(activity_repo)
        handler = TimeQueryHandler(storage)  # type: ignore

        start = time.perf_counter()
        result = handler.query_duration("shower")
        elapsed = time.perf_counter() - start

        assert result.success is True
        assert elapsed < 2.0

    def test_duration_query_with_1000_events(
        self, activity_repo: ActivityRepository
    ) -> None:
        """Test duration query latency with 1000 activities."""
        from ara.storage.queries import TimeQueryHandler

        class MinimalStorage:
            def __init__(self, activities: ActivityRepository):
                self.activities = activities
                self.events = None

        # Seed 1000 activities
        for i in range(1000):
            activity_repo.save(
                ActivityDTO(
                    name="workout" if i % 2 == 0 else "shower",
                    status=ActivityStatus.COMPLETED,
                    start_event_id=f"event-{i}",
                    start_time=datetime.now(UTC) - timedelta(minutes=i),
                    start_text="starting activity",
                    pairing_score=0.9,
                    duration_ms=15 * 60 * 1000,
                )
            )

        storage = MinimalStorage(activity_repo)
        handler = TimeQueryHandler(storage)  # type: ignore

        start = time.perf_counter()
        result = handler.query_duration("shower")
        elapsed = time.perf_counter() - start

        assert result.success is True
        assert elapsed < 2.0, f"Query took {elapsed:.3f}s with 1000 activities"


@pytest.mark.benchmark
class TestAroundTimeQueryLatency:
    """Benchmark tests for around-time query performance (SC-002)."""

    def test_around_time_query_under_2_seconds(
        self, storage_facade: "BenchmarkStorage", seeded_data: dict[str, int]
    ) -> None:
        """Test around-time query completes under 2 seconds."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(storage_facade)

        time_point = datetime.now(UTC).replace(hour=10, minute=0)

        start = time.perf_counter()
        result = handler.query_around_time(time_point, window_minutes=30)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"Around-time query took {elapsed:.3f}s, should be < 2s"


@pytest.mark.benchmark
class TestRangeQueryLatency:
    """Benchmark tests for range query performance (SC-002)."""

    def test_range_query_under_2_seconds(
        self, storage_facade: "BenchmarkStorage", seeded_data: dict[str, int]
    ) -> None:
        """Test range query over 30 days completes under 2 seconds."""
        from ara.storage.queries import TimeQueryHandler

        handler = TimeQueryHandler(storage_facade)

        now = datetime.now(UTC)
        start_time = now - timedelta(days=30)
        end_time = now

        start = time.perf_counter()
        result = handler.query_range(start_time, end_time)
        elapsed = time.perf_counter() - start

        assert elapsed < 2.0, f"Range query took {elapsed:.3f}s, should be < 2s"
        # With 10 events per day for 30 days, we should have 300 events
        assert len(result.events_found) >= 100  # At least some events returned
