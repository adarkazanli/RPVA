"""Integration tests for Claude query flow."""

from unittest.mock import MagicMock

import pytest

from ara.audio.mock_capture import MockAudioCapture, MockAudioPlayback
from ara.claude.client import ClaudeResponse
from ara.claude.handler import ClaudeHandler
from ara.feedback.audio import MockFeedback
from ara.llm.mock import MockLanguageModel
from ara.router.intent import IntentClassifier, IntentType
from ara.router.orchestrator import Orchestrator
from ara.stt.mock import MockTranscriber
from ara.tts.mock import MockSynthesizer
from ara.wake_word.mock import MockWakeWordDetector


class TestClaudeIntentFlow:
    """Integration tests for Claude intent classification."""

    @pytest.fixture
    def classifier(self) -> IntentClassifier:
        """Create an IntentClassifier instance."""
        return IntentClassifier()

    def test_claude_query_intent_flow(self, classifier: IntentClassifier) -> None:
        """Test Claude query intent classification patterns."""
        utterances = [
            ("ask claude what is the capital of france", IntentType.CLAUDE_QUERY),
            ("ask claude about quantum computing", IntentType.CLAUDE_QUERY),
            ("tell claude I need help with my code", IntentType.CLAUDE_QUERY),
            ("claude explain machine learning", IntentType.CLAUDE_QUERY),
        ]

        for text, expected_type in utterances:
            intent = classifier.classify(text)
            assert intent.type == expected_type, f"Failed for: {text}"

    def test_claude_summary_intent_flow(self, classifier: IntentClassifier) -> None:
        """Test Claude summary intent classification patterns."""
        utterances = [
            ("summarize my claude conversations today", IntentType.CLAUDE_SUMMARY),
            ("what did I ask claude today", IntentType.CLAUDE_SUMMARY),
            ("summarize my claude conversations this week", IntentType.CLAUDE_SUMMARY),
        ]

        for text, expected_type in utterances:
            intent = classifier.classify(text)
            assert intent.type == expected_type, f"Failed for: {text}"

    def test_claude_reset_intent_flow(self, classifier: IntentClassifier) -> None:
        """Test Claude reset intent classification patterns."""
        utterances = [
            ("new conversation", IntentType.CLAUDE_RESET),
            ("start over", IntentType.CLAUDE_RESET),
            ("clear conversation history", IntentType.CLAUDE_RESET),
            ("forget our conversation", IntentType.CLAUDE_RESET),
        ]

        for text, expected_type in utterances:
            intent = classifier.classify(text)
            assert intent.type == expected_type, f"Failed for: {text}"

    def test_claude_query_extracts_question(self, classifier: IntentClassifier) -> None:
        """Test that Claude query intent extracts the question."""
        intent = classifier.classify("ask claude what time is it in tokyo")
        assert intent.type == IntentType.CLAUDE_QUERY
        assert intent.entities.get("query") is not None
        assert "tokyo" in intent.entities["query"].lower()

    def test_claude_summary_extracts_period(self, classifier: IntentClassifier) -> None:
        """Test that Claude summary intent extracts the period."""
        intent = classifier.classify("summarize my claude conversations yesterday")
        assert intent.type == IntentType.CLAUDE_SUMMARY
        assert intent.entities.get("period") == "yesterday"


class TestClaudeHandlerFlow:
    """Integration tests for Claude handler operations."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        """Create mock Claude repository."""
        repo = MagicMock()
        repo.save_query.return_value = "query-123"
        repo.save_response.return_value = "response-456"
        repo.get_conversations_for_period.return_value = []
        return repo

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock Claude client."""
        client = MagicMock()
        client.check_connectivity.return_value = True
        client.send_message.return_value = ClaudeResponse(
            text="Paris is the capital of France.",
            tokens_used=25,
            model="claude-sonnet-4-20250514",
            latency_ms=150,
        )
        return client

    def test_query_flow_saves_to_repository(
        self, mock_repository: MagicMock, mock_client: MagicMock
    ) -> None:
        """Test that query flow saves query and response to repository."""
        handler = ClaudeHandler(repository=mock_repository)
        handler._client = mock_client

        response = handler.handle_query("What is the capital of France?")

        assert response == "Paris is the capital of France."
        mock_repository.save_query.assert_called_once()
        mock_repository.save_response.assert_called_once()

    def test_query_flow_maintains_session(
        self, mock_repository: MagicMock, mock_client: MagicMock
    ) -> None:
        """Test that query flow maintains conversation session."""
        handler = ClaudeHandler(repository=mock_repository)
        handler._client = mock_client

        # First query
        handler.handle_query("What is the capital of France?")

        # Verify session has history
        assert handler.has_conversation_history
        assert handler.is_in_followup_window()

    def test_followup_window_expires(
        self, mock_repository: MagicMock, mock_client: MagicMock
    ) -> None:
        """Test that follow-up window expires after timeout."""
        handler = ClaudeHandler(
            repository=mock_repository,
            followup_window_seconds=0.1,  # Very short for testing
        )
        handler._client = mock_client

        # First query
        handler.handle_query("What is the capital of France?")

        # Wait for window to expire
        import time

        time.sleep(0.2)

        # Follow-up window should have expired
        assert not handler.is_in_followup_window()

    def test_reset_clears_session(
        self, mock_repository: MagicMock, mock_client: MagicMock
    ) -> None:
        """Test that reset clears the conversation session."""
        handler = ClaudeHandler(repository=mock_repository)
        handler._client = mock_client

        # First query
        handler.handle_query("What is the capital of France?")
        assert handler.has_conversation_history

        # Reset
        message = handler.handle_reset()
        assert "cleared" in message.lower()
        assert not handler.has_conversation_history

    def test_summary_request_with_no_history(
        self, mock_repository: MagicMock
    ) -> None:
        """Test summary request when there's no conversation history."""
        mock_repository.get_conversations_for_period.return_value = []
        handler = ClaudeHandler(repository=mock_repository)

        summary = handler.handle_summary_request("today")

        assert "haven't had any" in summary.lower()

    def test_summary_request_with_history(
        self, mock_repository: MagicMock
    ) -> None:
        """Test summary request when there is conversation history."""
        mock_repository.get_conversations_for_period.return_value = [
            (
                {"utterance": "What is Python?", "_id": "q1"},
                {"text": "Python is a programming language.", "_id": "r1"},
            ),
            (
                {"utterance": "What is JavaScript?", "_id": "q2"},
                {"text": "JavaScript is a web programming language.", "_id": "r2"},
            ),
        ]
        handler = ClaudeHandler(repository=mock_repository)

        summary = handler.handle_summary_request("today")

        assert "2 conversation" in summary.lower()
        assert "Python" in summary
        assert "JavaScript" in summary


@pytest.mark.skip(reason="Orchestrator tests require full audio pipeline - use manual testing")
class TestClaudeOrchestratorIntegration:
    """Integration tests for Claude with orchestrator."""

    @pytest.fixture
    def orchestrator_with_claude(self) -> Orchestrator:
        """Create orchestrator with Claude support."""
        capture = MockAudioCapture(sample_rate=16000)
        playback = MockAudioPlayback()
        wake_word = MockWakeWordDetector()
        transcriber = MockTranscriber()
        llm = MockLanguageModel()
        synthesizer = MockSynthesizer()
        feedback = MockFeedback()

        wake_word.initialize(keywords=["ara"], sensitivity=0.5)
        transcriber.set_latency(0)
        llm.set_latency(0)
        synthesizer.set_latency(0)

        return Orchestrator(
            audio_capture=capture,
            audio_playback=playback,
            wake_word_detector=wake_word,
            transcriber=transcriber,
            language_model=llm,
            synthesizer=synthesizer,
            feedback=feedback,
        )

    def test_ask_claude_via_voice(
        self, orchestrator_with_claude: Orchestrator
    ) -> None:
        """Test asking Claude a question via voice command."""
        orchestrator = orchestrator_with_claude

        # Mock Claude handler
        mock_handler = MagicMock()
        mock_handler.handle_query.return_value = "Paris is the capital of France."
        mock_handler.is_in_followup_window.return_value = False
        orchestrator._claude_handler = mock_handler

        # Simulate voice input
        orchestrator._transcriber.set_response("ask claude what is the capital of france")
        orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        orchestrator._capture.set_audio_data(bytes(16000 * 2))

        result = orchestrator.process_single_interaction()

        assert result is not None
        # The response should be processed
        mock_handler.handle_query.assert_called_once()

    def test_new_conversation_via_voice(
        self, orchestrator_with_claude: Orchestrator
    ) -> None:
        """Test starting a new conversation via voice command."""
        orchestrator = orchestrator_with_claude

        # Mock Claude handler
        mock_handler = MagicMock()
        mock_handler.handle_reset.return_value = "Starting a new conversation."
        mock_handler.is_in_followup_window.return_value = False
        orchestrator._claude_handler = mock_handler

        # Simulate voice input
        orchestrator._transcriber.set_response("new conversation")
        orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        orchestrator._capture.set_audio_data(bytes(16000 * 2))

        result = orchestrator.process_single_interaction()

        assert result is not None
        mock_handler.handle_reset.assert_called_once()


class TestClaudeErrorHandling:
    """Integration tests for Claude error handling."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        """Create mock Claude repository."""
        repo = MagicMock()
        repo.save_query.return_value = "query-123"
        return repo

    def test_connectivity_error_provides_helpful_message(
        self, mock_repository: MagicMock
    ) -> None:
        """Test that connectivity errors provide helpful messages."""
        from ara.claude.errors import ClaudeConnectivityError

        handler = ClaudeHandler(repository=mock_repository)
        mock_client = MagicMock()
        mock_client.check_connectivity.side_effect = ClaudeConnectivityError(
            "Cannot reach Claude API"
        )
        handler._client = mock_client

        with pytest.raises(ClaudeConnectivityError):
            handler.handle_query("test query")

        # Error message should be available
        message = handler.get_connectivity_error_message()
        assert "internet" in message.lower() or "connection" in message.lower()

    def test_auth_error_provides_setup_guidance(
        self, mock_repository: MagicMock
    ) -> None:
        """Test that auth errors provide setup guidance."""
        handler = ClaudeHandler(repository=mock_repository)

        message = handler.get_auth_setup_message()
        assert "ANTHROPIC_API_KEY" in message
        assert "api key" in message.lower()

    def test_timeout_error_suggests_retry(
        self, mock_repository: MagicMock
    ) -> None:
        """Test that timeout errors suggest retry."""
        handler = ClaudeHandler(repository=mock_repository)

        message = handler.get_timeout_message()
        assert "try again" in message.lower()


class TestClaudeSessionManagement:
    """Integration tests for Claude session management."""

    @pytest.fixture
    def mock_repository(self) -> MagicMock:
        """Create mock Claude repository."""
        repo = MagicMock()
        repo.save_query.return_value = "query-123"
        repo.save_response.return_value = "response-456"
        return repo

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create mock Claude client."""
        client = MagicMock()
        client.check_connectivity.return_value = True
        client.send_message.return_value = ClaudeResponse(
            text="Test response",
            tokens_used=20,
            model="claude-sonnet-4-20250514",
            latency_ms=100,
        )
        return client

    def test_multi_turn_conversation(
        self, mock_repository: MagicMock, mock_client: MagicMock
    ) -> None:
        """Test multi-turn conversation maintains context."""
        handler = ClaudeHandler(repository=mock_repository)
        handler._client = mock_client

        # First turn
        handler.handle_query("What is Python?")

        # Second turn (follow-up)
        handler.handle_query("What are its main features?", is_followup=True)

        # Verify session accumulated messages
        assert mock_client.send_message.call_count == 2

        # Second call should include session context
        second_call_kwargs = mock_client.send_message.call_args_list[1]
        # Session parameter should be passed
        assert second_call_kwargs[1].get("session") is not None

    def test_session_id_consistent_within_conversation(
        self, mock_repository: MagicMock, mock_client: MagicMock
    ) -> None:
        """Test session ID remains consistent within a conversation."""
        handler = ClaudeHandler(repository=mock_repository)
        handler._client = mock_client

        session_id_1 = handler.session_id
        handler.handle_query("First question")

        session_id_2 = handler.session_id
        handler.handle_query("Second question")

        assert session_id_1 == session_id_2

    def test_session_id_preserved_after_reset(
        self, mock_repository: MagicMock, mock_client: MagicMock
    ) -> None:
        """Test session ID is preserved after reset (history cleared, ID kept)."""
        handler = ClaudeHandler(repository=mock_repository)
        handler._client = mock_client

        handler.handle_query("First question")
        original_session_id = handler.session_id
        assert handler.has_conversation_history

        handler.reset_session()

        # Session ID is preserved by design
        assert handler.session_id == original_session_id
        # But history is cleared
        assert not handler.has_conversation_history
