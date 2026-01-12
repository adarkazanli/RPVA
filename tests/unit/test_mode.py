"""Unit tests for ModeManager and mode persistence (T105)."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestModeManagerPersistence:
    """Tests for ModeManager with preference persistence."""

    def test_save_mode_preference(self) -> None:
        """Test mode preference is saved to file."""
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_path = Path(tmpdir) / "preferences.json"

            monitor = NetworkMonitor()
            manager = ModeManager(
                network_monitor=monitor,
                preferences_path=prefs_path,
            )

            manager.set_mode(OperationMode.ONLINE_CLOUD)
            manager.save_preferences()

            assert prefs_path.exists()
            data = json.loads(prefs_path.read_text())
            assert data["mode"] == "online_cloud"

    def test_load_mode_preference(self) -> None:
        """Test mode preference is loaded from file."""
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_path = Path(tmpdir) / "preferences.json"
            prefs_path.write_text(json.dumps({"mode": "online_local"}))

            monitor = NetworkMonitor()
            manager = ModeManager(
                network_monitor=monitor,
                preferences_path=prefs_path,
            )
            manager.load_preferences()

            assert manager.mode == OperationMode.ONLINE_LOCAL

    def test_load_preferences_file_not_exists(self) -> None:
        """Test graceful handling when preferences file doesn't exist."""
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_path = Path(tmpdir) / "nonexistent.json"

            monitor = NetworkMonitor()
            manager = ModeManager(
                network_monitor=monitor,
                preferences_path=prefs_path,
            )
            manager.load_preferences()

            # Should keep default mode
            assert manager.mode == OperationMode.OFFLINE

    def test_load_preferences_invalid_json(self) -> None:
        """Test graceful handling of invalid JSON."""
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_path = Path(tmpdir) / "preferences.json"
            prefs_path.write_text("not valid json")

            monitor = NetworkMonitor()
            manager = ModeManager(
                network_monitor=monitor,
                preferences_path=prefs_path,
            )
            manager.load_preferences()

            # Should keep default mode
            assert manager.mode == OperationMode.OFFLINE

    def test_load_preferences_invalid_mode(self) -> None:
        """Test graceful handling of invalid mode value."""
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        with tempfile.TemporaryDirectory() as tmpdir:
            prefs_path = Path(tmpdir) / "preferences.json"
            prefs_path.write_text(json.dumps({"mode": "invalid_mode"}))

            monitor = NetworkMonitor()
            manager = ModeManager(
                network_monitor=monitor,
                preferences_path=prefs_path,
            )
            manager.load_preferences()

            # Should keep default mode
            assert manager.mode == OperationMode.OFFLINE


class TestModeManagerStatusInfo:
    """Tests for ModeManager status information."""

    def test_get_status_info(self) -> None:
        """Test getting comprehensive status information."""
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

        status = manager.get_status()

        assert status["mode"] == "online_local"
        assert status["network_status"] == "online"
        assert status["forced_offline"] is False

    def test_get_status_info_forced_offline(self) -> None:
        """Test status info when forced offline."""
        from ara.router.mode import (
            ModeManager,
            NetworkMonitor,
            NetworkStatus,
            OperationMode,
        )

        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.ONLINE
        manager = ModeManager(network_monitor=monitor)
        manager.go_offline()

        status = manager.get_status()

        assert status["mode"] == "offline"
        assert status["forced_offline"] is True

    def test_get_mode_description(self) -> None:
        """Test human-readable mode descriptions."""
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        monitor = NetworkMonitor()
        manager = ModeManager(network_monitor=monitor)

        manager._mode = OperationMode.OFFLINE
        assert "offline" in manager.get_mode_description().lower()

        manager._mode = OperationMode.ONLINE_LOCAL
        assert "online" in manager.get_mode_description().lower()

        manager._mode = OperationMode.ONLINE_CLOUD
        assert "cloud" in manager.get_mode_description().lower()


class TestModeManagerCallbacks:
    """Tests for ModeManager event callbacks."""

    def test_on_mode_change_callback(self) -> None:
        """Test callback is invoked on mode change."""
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        callback_data: list[tuple[OperationMode, OperationMode]] = []

        def on_mode_change(old_mode: OperationMode, new_mode: OperationMode) -> None:
            callback_data.append((old_mode, new_mode))

        monitor = NetworkMonitor()
        manager = ModeManager(
            network_monitor=monitor,
            on_mode_change=on_mode_change,
        )

        manager.set_mode(OperationMode.ONLINE_LOCAL)

        assert len(callback_data) == 1
        assert callback_data[0][0] == OperationMode.OFFLINE
        assert callback_data[0][1] == OperationMode.ONLINE_LOCAL

    def test_no_callback_on_same_mode(self) -> None:
        """Test callback not invoked when mode unchanged."""
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        callback_count = [0]

        def on_mode_change(old_mode: OperationMode, new_mode: OperationMode) -> None:
            callback_count[0] += 1

        monitor = NetworkMonitor()
        manager = ModeManager(
            network_monitor=monitor,
            on_mode_change=on_mode_change,
        )

        # Set same mode twice
        manager.set_mode(OperationMode.OFFLINE)

        assert callback_count[0] == 0  # No change, no callback


class TestModeManagerAutoSwitch:
    """Tests for automatic mode switching based on network status."""

    def test_auto_switch_to_offline_on_network_loss(self) -> None:
        """Test automatic switch to offline when network is lost."""
        from ara.router.mode import (
            ModeManager,
            NetworkMonitor,
            NetworkStatus,
            OperationMode,
        )

        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.ONLINE
        manager = ModeManager(
            network_monitor=monitor,
            auto_mode_switching=True,
        )
        manager._mode = OperationMode.ONLINE_LOCAL

        # Simulate network loss
        manager.on_network_status_change(NetworkStatus.OFFLINE)

        # Should switch to offline mode
        assert manager.mode == OperationMode.OFFLINE

    def test_auto_switch_preserves_forced_offline(self) -> None:
        """Test forced offline is preserved even when network comes back."""
        from ara.router.mode import (
            ModeManager,
            NetworkMonitor,
            NetworkStatus,
            OperationMode,
        )

        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.OFFLINE
        manager = ModeManager(
            network_monitor=monitor,
            auto_mode_switching=True,
        )
        manager.go_offline()

        # Simulate network restoration
        monitor._status = NetworkStatus.ONLINE
        manager.on_network_status_change(NetworkStatus.ONLINE)

        # Should remain offline because user forced it
        assert manager.mode == OperationMode.OFFLINE
        assert manager.is_forced_offline is True

    def test_no_auto_switch_when_disabled(self) -> None:
        """Test no automatic switching when disabled."""
        from ara.router.mode import (
            ModeManager,
            NetworkMonitor,
            NetworkStatus,
            OperationMode,
        )

        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.ONLINE
        manager = ModeManager(
            network_monitor=monitor,
            auto_mode_switching=False,
        )
        manager._mode = OperationMode.ONLINE_LOCAL

        # Simulate network loss
        manager.on_network_status_change(NetworkStatus.OFFLINE)

        # Should remain in current mode
        assert manager.mode == OperationMode.ONLINE_LOCAL
