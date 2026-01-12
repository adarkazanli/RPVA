"""Network monitoring and operation mode management.

Provides connectivity detection, mode switching, and routing decisions.
"""

import socket
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class NetworkStatus(Enum):
    """Network connectivity status."""

    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class OperationMode(Enum):
    """Voice assistant operation mode.

    - OFFLINE: Local LLM only, no network features
    - ONLINE_LOCAL: Online but prefer local LLM
    - ONLINE_CLOUD: Online with cloud LLM for complex queries
    """

    OFFLINE = "offline"
    ONLINE_LOCAL = "online_local"
    ONLINE_CLOUD = "online_cloud"


class NetworkMonitor:
    """Monitors network connectivity status.

    Performs periodic connectivity checks and notifies on status changes.
    """

    # Hosts to check connectivity against
    CHECK_HOSTS = [
        ("8.8.8.8", 53),  # Google DNS
        ("1.1.1.1", 53),  # Cloudflare DNS
    ]
    TIMEOUT_SECONDS = 3

    def __init__(
        self,
        check_interval: int = 30,
        on_status_change: Callable[[NetworkStatus], None] | None = None,
    ) -> None:
        """Initialize the network monitor.

        Args:
            check_interval: Seconds between connectivity checks.
            on_status_change: Callback when status changes.
        """
        self._check_interval = check_interval
        self._on_status_change = on_status_change
        self._status = NetworkStatus.UNKNOWN
        self._running = False
        self._thread: threading.Thread | None = None

    @property
    def check_interval(self) -> int:
        """Get the check interval in seconds."""
        return self._check_interval

    @property
    def status(self) -> NetworkStatus:
        """Get current network status."""
        return self._status

    @property
    def is_online(self) -> bool:
        """Check if currently online."""
        return self._status == NetworkStatus.ONLINE

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running

    def check_connectivity(self) -> NetworkStatus:
        """Check network connectivity.

        Attempts to connect to known hosts to verify internet access.

        Returns:
            NetworkStatus indicating connectivity state.
        """
        for host, port in self.CHECK_HOSTS:
            try:
                with socket.create_connection(
                    (host, port), timeout=self.TIMEOUT_SECONDS
                ):
                    return NetworkStatus.ONLINE
            except OSError:
                continue

        return NetworkStatus.OFFLINE

    def start(self) -> None:
        """Start background connectivity monitoring."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background connectivity monitoring."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            new_status = self.check_connectivity()

            if new_status != self._status:
                old_status = self._status
                self._status = new_status
                self._notify_status_change(new_status)

            time.sleep(self._check_interval)

    def _notify_status_change(self, new_status: NetworkStatus) -> None:
        """Notify listeners of status change."""
        if self._on_status_change is not None:
            try:
                self._on_status_change(new_status)
            except Exception:
                pass  # Don't let callback errors crash the monitor


class ModeManager:
    """Manages voice assistant operation mode.

    Handles mode switching and provides routing decisions based on
    network status and user preferences.
    """

    def __init__(
        self,
        network_monitor: NetworkMonitor,
        default_mode: OperationMode = OperationMode.OFFLINE,
    ) -> None:
        """Initialize the mode manager.

        Args:
            network_monitor: Network monitor instance.
            default_mode: Initial operation mode.
        """
        self._network_monitor = network_monitor
        self._mode = default_mode
        self._forced_offline = False
        self._cloud_complexity_threshold = 0.7

    @property
    def mode(self) -> OperationMode:
        """Get current operation mode."""
        return self._mode

    @property
    def is_forced_offline(self) -> bool:
        """Check if offline mode is forced."""
        return self._forced_offline

    def set_mode(self, mode: OperationMode) -> None:
        """Set operation mode.

        Args:
            mode: New operation mode.
        """
        self._mode = mode
        if mode != OperationMode.OFFLINE:
            self._forced_offline = False

    def go_offline(self) -> None:
        """Force offline mode."""
        self._mode = OperationMode.OFFLINE
        self._forced_offline = True

    def go_online(self) -> None:
        """Switch to online mode if network available."""
        self._forced_offline = False

        if self._network_monitor.is_online:
            self._mode = OperationMode.ONLINE_LOCAL
        # If not online, stay in current mode

    def should_use_cloud(self, explicit_request: bool = False) -> bool:
        """Determine if cloud LLM should be used.

        Args:
            explicit_request: User explicitly requested internet/cloud.

        Returns:
            True if cloud should be used.
        """
        if self._mode == OperationMode.OFFLINE:
            return False

        if not self._network_monitor.is_online:
            return False

        if self._mode == OperationMode.ONLINE_CLOUD:
            return True

        if explicit_request:
            return True

        return False

    def should_use_cloud_for_query(
        self,
        complexity_score: float,
        explicit_request: bool = False,
    ) -> bool:
        """Determine if cloud should be used for a specific query.

        Args:
            complexity_score: Query complexity score (0.0-1.0).
            explicit_request: User explicitly requested internet/cloud.

        Returns:
            True if cloud should be used.
        """
        if not self.should_use_cloud(explicit_request):
            return False

        # Use cloud for complex queries in ONLINE_CLOUD mode
        if self._mode == OperationMode.ONLINE_CLOUD:
            return complexity_score >= self._cloud_complexity_threshold

        # With explicit request, always use cloud
        if explicit_request:
            return True

        return False


__all__ = [
    "ModeManager",
    "NetworkMonitor",
    "NetworkStatus",
    "OperationMode",
]
