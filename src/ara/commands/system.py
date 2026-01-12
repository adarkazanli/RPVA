"""System command handlers for mode control and status.

Handles voice commands for controlling the assistant's operation mode.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..router.mode import ModeManager


class SystemCommandHandler:
    """Handles system-level voice commands.

    Supports:
    - "go offline" / "offline" - Switch to offline mode
    - "go online" / "online" - Switch to online mode
    - "status" / "what mode" - Report current status
    """

    def __init__(self, mode_manager: "ModeManager") -> None:
        """Initialize the handler.

        Args:
            mode_manager: ModeManager instance to control.
        """
        self._mode_manager = mode_manager

    def handle(self, command: str) -> str:
        """Handle a system command.

        Args:
            command: Command string (offline, online, status).

        Returns:
            Response string to speak.
        """
        command = command.lower().strip()

        if command == "offline":
            return self._handle_go_offline()
        elif command == "online":
            return self._handle_go_online()
        elif command == "status":
            return self._handle_status()
        else:
            return f"Unknown system command: {command}"

    def _handle_go_offline(self) -> str:
        """Handle go offline command."""
        self._mode_manager.go_offline()
        return "I'm now offline. All processing will be done locally."

    def _handle_go_online(self) -> str:
        """Handle go online command."""
        self._mode_manager.go_online()

        status = self._mode_manager.get_status()
        if status["network_status"] == "online":
            return "I'm now online. Cloud features are available."
        else:
            return "I tried to go online but no network connection is available. Staying in offline mode."

    def _handle_status(self) -> str:
        """Handle status query command."""
        return self._mode_manager.get_mode_description()


__all__ = ["SystemCommandHandler"]
