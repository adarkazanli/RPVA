"""Auto-close logic for stale activities.

Provides timeout checking to close activities that exceed a duration limit.
"""

import logging
from datetime import UTC, datetime, timedelta

from .models import Activity
from .tracker import ActivityRepository

logger = logging.getLogger(__name__)

# Default timeout: 4 hours
DEFAULT_TIMEOUT_HOURS = 4.0


class ActivityTimeout:
    """Handles auto-closing of stale activities.

    Activities exceeding the timeout duration are automatically
    closed to prevent indefinitely running activities.
    """

    def __init__(
        self,
        repository: ActivityRepository | None = None,
        timeout_hours: float = DEFAULT_TIMEOUT_HOURS,
    ) -> None:
        """Initialize timeout handler.

        Args:
            repository: Repository for activity persistence
            timeout_hours: Hours after which to auto-close (default: 4)
        """
        self._repository = repository
        self._timeout_hours = timeout_hours

    def check_and_close_stale(self) -> list[Activity]:
        """Check for and auto-close activities exceeding timeout.

        Returns:
            List of activities that were auto-closed
        """
        if not self._repository:
            logger.debug("No repository configured, skipping timeout check")
            return []

        closed: list[Activity] = []
        now = datetime.now(UTC)
        cutoff = now - timedelta(hours=self._timeout_hours)

        # Find all active activities that started before cutoff
        # This would require a custom repository method in practice
        # For now, we'll check the single active activity
        try:
            # Get active activity for default user
            doc = self._repository.find_active("default")
            if doc:
                activity = Activity.from_dict(doc)

                if activity.start_time < cutoff:
                    # Auto-close at the cutoff time, not now
                    activity.complete(end_time=cutoff, auto_closed=True)

                    if activity.id:
                        self._repository.update(activity.id, activity.to_dict())

                    logger.info(
                        f"Auto-closed stale activity '{activity.name}' "
                        f"(started {self._timeout_hours}+ hours ago)"
                    )
                    closed.append(activity)

        except Exception as e:
            logger.error(f"Error checking for stale activities: {e}")

        return closed


__all__ = ["ActivityTimeout", "DEFAULT_TIMEOUT_HOURS"]
