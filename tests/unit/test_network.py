"""Unit tests for network connectivity detection."""

from unittest.mock import MagicMock, patch

import pytest


class TestNetworkStatus:
    """Tests for NetworkStatus enum."""

    def test_status_values(self) -> None:
        """Test NetworkStatus enum has expected values."""
        from ara.router.mode import NetworkStatus

        assert NetworkStatus.ONLINE.value == "online"
        assert NetworkStatus.OFFLINE.value == "offline"
        assert NetworkStatus.UNKNOWN.value == "unknown"


class TestNetworkMonitor:
    """Tests for NetworkMonitor class."""

    def test_create_network_monitor(self) -> None:
        """Test creating a NetworkMonitor instance."""
        from ara.router.mode import NetworkMonitor

        monitor = NetworkMonitor()
        assert monitor is not None
        assert monitor.check_interval == 30  # Default 30s

    def test_create_with_custom_interval(self) -> None:
        """Test creating monitor with custom check interval."""
        from ara.router.mode import NetworkMonitor

        monitor = NetworkMonitor(check_interval=60)
        assert monitor.check_interval == 60

    @patch("socket.create_connection")
    def test_check_connectivity_online(self, mock_socket: MagicMock) -> None:
        """Test connectivity check when online."""
        from ara.router.mode import NetworkMonitor, NetworkStatus

        mock_socket.return_value.__enter__ = MagicMock()
        mock_socket.return_value.__exit__ = MagicMock()

        monitor = NetworkMonitor()
        status = monitor.check_connectivity()

        assert status == NetworkStatus.ONLINE

    @patch("socket.create_connection")
    def test_check_connectivity_offline(self, mock_socket: MagicMock) -> None:
        """Test connectivity check when offline."""
        from ara.router.mode import NetworkMonitor, NetworkStatus

        mock_socket.side_effect = OSError("No network")

        monitor = NetworkMonitor()
        status = monitor.check_connectivity()

        assert status == NetworkStatus.OFFLINE

    def test_is_online_property(self) -> None:
        """Test is_online convenience property."""
        from ara.router.mode import NetworkMonitor, NetworkStatus

        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.ONLINE
        assert monitor.is_online is True

        monitor._status = NetworkStatus.OFFLINE
        assert monitor.is_online is False

    def test_status_property(self) -> None:
        """Test status property returns current status."""
        from ara.router.mode import NetworkMonitor, NetworkStatus

        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.ONLINE
        assert monitor.status == NetworkStatus.ONLINE

    @patch("socket.create_connection")
    def test_start_monitoring(self, mock_socket: MagicMock) -> None:
        """Test starting background monitoring."""
        from ara.router.mode import NetworkMonitor

        mock_socket.return_value.__enter__ = MagicMock()
        mock_socket.return_value.__exit__ = MagicMock()

        monitor = NetworkMonitor(check_interval=1)
        monitor.start()

        assert monitor.is_running is True

        monitor.stop()
        assert monitor.is_running is False

    def test_on_status_change_callback(self) -> None:
        """Test callback is invoked on status change."""
        from ara.router.mode import NetworkMonitor, NetworkStatus

        callback_data: list[NetworkStatus] = []

        def on_change(new_status: NetworkStatus) -> None:
            callback_data.append(new_status)

        monitor = NetworkMonitor(on_status_change=on_change)

        # Simulate status change
        monitor._status = NetworkStatus.OFFLINE
        monitor._notify_status_change(NetworkStatus.ONLINE)

        assert len(callback_data) == 1
        assert callback_data[0] == NetworkStatus.ONLINE


class TestOperationMode:
    """Tests for OperationMode enum."""

    def test_mode_values(self) -> None:
        """Test OperationMode enum has expected values."""
        from ara.router.mode import OperationMode

        assert OperationMode.OFFLINE.value == "offline"
        assert OperationMode.ONLINE_LOCAL.value == "online_local"
        assert OperationMode.ONLINE_CLOUD.value == "online_cloud"


class TestModeManager:
    """Tests for ModeManager class."""

    def test_create_mode_manager(self) -> None:
        """Test creating a ModeManager instance."""
        from ara.router.mode import ModeManager, NetworkMonitor

        monitor = NetworkMonitor()
        manager = ModeManager(network_monitor=monitor)

        assert manager is not None

    def test_default_mode_is_offline(self) -> None:
        """Test default mode is offline."""
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        monitor = NetworkMonitor()
        manager = ModeManager(network_monitor=monitor)

        assert manager.mode == OperationMode.OFFLINE

    def test_set_mode_manual(self) -> None:
        """Test manually setting operation mode."""
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        monitor = NetworkMonitor()
        manager = ModeManager(network_monitor=monitor)

        manager.set_mode(OperationMode.ONLINE_LOCAL)
        assert manager.mode == OperationMode.ONLINE_LOCAL

    def test_force_offline_mode(self) -> None:
        """Test forcing offline mode."""
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        monitor = NetworkMonitor()
        manager = ModeManager(network_monitor=monitor)

        manager.go_offline()
        assert manager.mode == OperationMode.OFFLINE
        assert manager.is_forced_offline is True

    def test_go_online_when_available(self) -> None:
        """Test switching to online mode."""
        from ara.router.mode import (
            ModeManager,
            NetworkMonitor,
            NetworkStatus,
            OperationMode,
        )

        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.ONLINE
        manager = ModeManager(network_monitor=monitor)
        manager._mode = OperationMode.OFFLINE

        manager.go_online()
        assert manager.mode == OperationMode.ONLINE_LOCAL

    def test_go_online_when_offline_stays_offline(self) -> None:
        """Test go_online when network unavailable stays offline."""
        from ara.router.mode import (
            ModeManager,
            NetworkMonitor,
            NetworkStatus,
            OperationMode,
        )

        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.OFFLINE
        manager = ModeManager(network_monitor=monitor)

        manager.go_online()
        assert manager.mode == OperationMode.OFFLINE

    def test_should_use_cloud(self) -> None:
        """Test should_use_cloud logic."""
        from ara.router.mode import (
            ModeManager,
            NetworkMonitor,
            NetworkStatus,
            OperationMode,
        )

        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.ONLINE
        manager = ModeManager(network_monitor=monitor)

        # Offline mode - never use cloud
        manager._mode = OperationMode.OFFLINE
        assert manager.should_use_cloud() is False

        # Online local - don't use cloud by default
        manager._mode = OperationMode.ONLINE_LOCAL
        assert manager.should_use_cloud() is False

        # Online cloud - use cloud
        manager._mode = OperationMode.ONLINE_CLOUD
        assert manager.should_use_cloud() is True

    def test_should_use_cloud_with_explicit_request(self) -> None:
        """Test should_use_cloud with explicit internet request."""
        from ara.router.mode import (
            ModeManager,
            NetworkMonitor,
            NetworkStatus,
            OperationMode,
        )

        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.ONLINE
        manager = ModeManager(network_monitor=monitor)
        manager._mode = OperationMode.ONLINE_LOCAL

        # Explicit request should allow cloud
        assert manager.should_use_cloud(explicit_request=True) is True
