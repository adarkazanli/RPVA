"""Integration tests for mode switching flow (T106)."""




class TestModeSwitchingViaVoice:
    """Tests for voice-triggered mode switching."""

    def test_go_offline_command(self) -> None:
        """Test 'go offline' voice command switches mode."""
        from ara.router.intent import IntentClassifier, IntentType
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        # Parse command
        classifier = IntentClassifier()
        intent = classifier.classify("go offline")

        assert intent.type == IntentType.SYSTEM_COMMAND
        assert intent.entities.get("command") == "offline"

        # Execute command
        monitor = NetworkMonitor()
        manager = ModeManager(network_monitor=monitor)
        manager._mode = OperationMode.ONLINE_LOCAL

        # Simulate command handling
        if intent.entities.get("command") == "offline":
            manager.go_offline()

        assert manager.mode == OperationMode.OFFLINE
        assert manager.is_forced_offline is True

    def test_go_online_command(self) -> None:
        """Test 'go online' voice command switches mode."""
        from ara.router.intent import IntentClassifier, IntentType
        from ara.router.mode import (
            ModeManager,
            NetworkMonitor,
            NetworkStatus,
            OperationMode,
        )

        # Parse command
        classifier = IntentClassifier()
        intent = classifier.classify("go online")

        assert intent.type == IntentType.SYSTEM_COMMAND
        assert intent.entities.get("command") == "online"

        # Execute command with network available
        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.ONLINE
        manager = ModeManager(network_monitor=monitor)
        manager.go_offline()

        # Simulate command handling
        if intent.entities.get("command") == "online":
            manager.go_online()

        assert manager.mode == OperationMode.ONLINE_LOCAL
        assert manager.is_forced_offline is False

    def test_status_query_command(self) -> None:
        """Test 'what mode are you in' returns status."""
        from ara.router.intent import IntentClassifier, IntentType
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        # Parse command
        classifier = IntentClassifier()
        intent = classifier.classify("what mode are you in")

        assert intent.type == IntentType.SYSTEM_COMMAND
        assert intent.entities.get("command") == "status"

        # Get status
        monitor = NetworkMonitor()
        manager = ModeManager(network_monitor=monitor)
        manager._mode = OperationMode.OFFLINE

        status = manager.get_status()
        assert status["mode"] == "offline"


class TestModeAndNetworkIntegration:
    """Tests for mode and network status integration."""

    def test_network_monitor_triggers_mode_change(self) -> None:
        """Test network monitor callback triggers mode change."""
        from ara.router.mode import (
            ModeManager,
            NetworkMonitor,
            NetworkStatus,
            OperationMode,
        )

        mode_changes: list[tuple[OperationMode, OperationMode]] = []

        def on_mode_change(old: OperationMode, new: OperationMode) -> None:
            mode_changes.append((old, new))

        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.ONLINE
        manager = ModeManager(
            network_monitor=monitor,
            on_mode_change=on_mode_change,
            auto_mode_switching=True,
        )
        manager._mode = OperationMode.ONLINE_LOCAL

        # Simulate network loss notification
        manager.on_network_status_change(NetworkStatus.OFFLINE)

        assert manager.mode == OperationMode.OFFLINE
        assert len(mode_changes) == 1
        assert mode_changes[0] == (OperationMode.ONLINE_LOCAL, OperationMode.OFFLINE)


class TestSystemCommandHandling:
    """Tests for system command handlers."""

    def test_system_command_handler_go_offline(self) -> None:
        """Test system command handler for go offline."""
        from ara.commands.system import SystemCommandHandler
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        monitor = NetworkMonitor()
        manager = ModeManager(network_monitor=monitor)
        manager._mode = OperationMode.ONLINE_LOCAL

        handler = SystemCommandHandler(mode_manager=manager)
        response = handler.handle("offline")

        assert manager.mode == OperationMode.OFFLINE
        assert "offline" in response.lower()

    def test_system_command_handler_go_online(self) -> None:
        """Test system command handler for go online."""
        from ara.commands.system import SystemCommandHandler
        from ara.router.mode import (
            ModeManager,
            NetworkMonitor,
            NetworkStatus,
            OperationMode,
        )

        monitor = NetworkMonitor()
        monitor._status = NetworkStatus.ONLINE
        manager = ModeManager(network_monitor=monitor)

        handler = SystemCommandHandler(mode_manager=manager)
        response = handler.handle("online")

        assert manager.mode == OperationMode.ONLINE_LOCAL
        assert "online" in response.lower()

    def test_system_command_handler_status(self) -> None:
        """Test system command handler for status query."""
        from ara.commands.system import SystemCommandHandler
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode

        monitor = NetworkMonitor()
        manager = ModeManager(network_monitor=monitor)
        manager._mode = OperationMode.OFFLINE

        handler = SystemCommandHandler(mode_manager=manager)
        response = handler.handle("status")

        assert "offline" in response.lower()


class TestModeWithOrchestratorIntegration:
    """Tests for mode integration with orchestrator."""

    def test_orchestrator_handles_system_command(self) -> None:
        """Test orchestrator routes system commands correctly."""
        from ara.feedback.audio import MockFeedback
        from ara.llm.mock import MockLanguageModel
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode
        from ara.router.orchestrator import Orchestrator

        # Setup
        llm = MockLanguageModel()
        feedback = MockFeedback()
        monitor = NetworkMonitor()
        mode_manager = ModeManager(network_monitor=monitor)
        mode_manager._mode = OperationMode.ONLINE_LOCAL

        orchestrator = Orchestrator(
            llm=llm,
            feedback=feedback,
            mode_manager=mode_manager,
        )

        # Test go offline command
        response = orchestrator.process("go offline")

        assert mode_manager.mode == OperationMode.OFFLINE
        assert "offline" in response.lower()

    def test_mode_change_triggers_feedback(self) -> None:
        """Test mode change plays audio feedback."""
        from ara.feedback import FeedbackType
        from ara.feedback.audio import MockFeedback
        from ara.llm.mock import MockLanguageModel
        from ara.router.mode import ModeManager, NetworkMonitor, OperationMode
        from ara.router.orchestrator import Orchestrator

        llm = MockLanguageModel()
        feedback = MockFeedback()
        monitor = NetworkMonitor()
        mode_manager = ModeManager(network_monitor=monitor)
        mode_manager._mode = OperationMode.ONLINE_LOCAL

        orchestrator = Orchestrator(
            llm=llm,
            feedback=feedback,
            mode_manager=mode_manager,
        )

        # Execute mode change
        orchestrator.process("go offline")

        # Should have played mode change feedback
        assert FeedbackType.MODE_CHANGE in feedback.events
