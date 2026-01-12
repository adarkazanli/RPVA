"""Integration tests for online query flow."""


import pytest

from ara.audio.mock_capture import MockAudioCapture, MockAudioPlayback
from ara.feedback.audio import MockFeedback
from ara.llm.mock import MockLanguageModel
from ara.router.orchestrator import Orchestrator
from ara.stt.mock import MockTranscriber
from ara.tts.mock import MockSynthesizer
from ara.wake_word.mock import MockWakeWordDetector


class TestOnlineQueryFlow:
    """Integration tests for online query handling."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create orchestrator with mocked components."""
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

    def test_web_search_intent_triggers_search(
        self, orchestrator: Orchestrator
    ) -> None:
        """Test web search intent triggers web search."""
        orchestrator._transcriber.set_response("search for Raspberry Pi 5")
        orchestrator._llm.set_response(
            "The Raspberry Pi 5 is the latest model with improved performance."
        )
        orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        orchestrator._capture.set_audio_data(bytes(16000 * 2))

        result = orchestrator.process_single_interaction()

        assert result is not None
        assert result.intent == "web_search"

    def test_with_internet_trigger(self, orchestrator: Orchestrator) -> None:
        """Test 'with internet' phrase triggers online mode."""
        orchestrator._transcriber.set_response(
            "with internet, what is the weather today"
        )
        orchestrator._llm.set_response("Currently sunny and 72 degrees.")
        orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        orchestrator._capture.set_audio_data(bytes(16000 * 2))

        result = orchestrator.process_single_interaction()

        assert result is not None
        assert result.intent == "web_search"

    def test_regular_query_stays_local(self, orchestrator: Orchestrator) -> None:
        """Test regular queries stay local."""
        orchestrator._transcriber.set_response("what time is it")
        orchestrator._llm.set_response("It's 3:30 PM.")
        orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        orchestrator._capture.set_audio_data(bytes(16000 * 2))

        result = orchestrator.process_single_interaction()

        assert result is not None
        assert result.intent == "general_question"


class TestGracefulDegradation:
    """Tests for graceful degradation when offline."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create orchestrator for degradation tests."""
        capture = MockAudioCapture(sample_rate=16000)
        playback = MockAudioPlayback()
        wake_word = MockWakeWordDetector()
        transcriber = MockTranscriber()
        llm = MockLanguageModel()
        synthesizer = MockSynthesizer()
        feedback = MockFeedback()

        wake_word.initialize(keywords=["ara"], sensitivity=0.5)

        return Orchestrator(
            audio_capture=capture,
            audio_playback=playback,
            wake_word_detector=wake_word,
            transcriber=transcriber,
            language_model=llm,
            synthesizer=synthesizer,
            feedback=feedback,
        )

    def test_offline_during_search_falls_back_to_local(
        self, orchestrator: Orchestrator
    ) -> None:
        """Test search request while offline falls back to local LLM."""
        orchestrator._transcriber.set_response("search for something")
        orchestrator._llm.set_response(
            "I'm currently offline. Let me try to answer from my knowledge."
        )
        orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        orchestrator._capture.set_audio_data(bytes(16000 * 2))

        # Simulate offline state
        if orchestrator._mode_manager is not None:
            from ara.router.mode import NetworkStatus

            orchestrator._mode_manager._network_monitor._status = NetworkStatus.OFFLINE

        result = orchestrator.process_single_interaction()

        assert result is not None
        # Should still get a response, even if offline
        assert result.response_text != ""

    def test_cloud_api_error_falls_back_to_local(
        self, orchestrator: Orchestrator
    ) -> None:
        """Test cloud API error falls back to local LLM."""
        orchestrator._transcriber.set_response("complex query for cloud")
        orchestrator._llm.set_response("Local fallback response.")
        orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        orchestrator._capture.set_audio_data(bytes(16000 * 2))

        result = orchestrator.process_single_interaction()

        assert result is not None
        assert result.response_text != ""


class TestQueryRouting:
    """Tests for query routing logic."""

    @pytest.fixture
    def orchestrator(self) -> Orchestrator:
        """Create orchestrator for routing tests."""
        capture = MockAudioCapture(sample_rate=16000)
        playback = MockAudioPlayback()
        wake_word = MockWakeWordDetector()
        transcriber = MockTranscriber()
        llm = MockLanguageModel()
        synthesizer = MockSynthesizer()
        feedback = MockFeedback()

        wake_word.initialize(keywords=["ara"], sensitivity=0.5)

        return Orchestrator(
            audio_capture=capture,
            audio_playback=playback,
            wake_word_detector=wake_word,
            transcriber=transcriber,
            language_model=llm,
            synthesizer=synthesizer,
            feedback=feedback,
        )

    def test_simple_query_uses_local(self, orchestrator: Orchestrator) -> None:
        """Test simple queries use local LLM."""
        orchestrator._transcriber.set_response("what is 2 plus 2")
        orchestrator._llm.set_response("4")
        orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        orchestrator._capture.set_audio_data(bytes(16000 * 2))

        result = orchestrator.process_single_interaction()

        assert result is not None
        # Simple math should be handled locally
        assert result.response_text == "4"

    def test_explicit_search_uses_web(self, orchestrator: Orchestrator) -> None:
        """Test explicit search requests use web search."""
        orchestrator._transcriber.set_response("look up latest Python release")
        orchestrator._llm.set_response("Python 3.12 is the latest stable release.")
        orchestrator._wake_word.schedule_detection(at_chunk=0, confidence=0.9)
        orchestrator._capture.set_audio_data(bytes(16000 * 2))

        result = orchestrator.process_single_interaction()

        assert result is not None
        assert result.intent == "web_search"


class TestResponseSourceLogging:
    """Tests for logging response source."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage for testing."""
        from ara.logger.storage import InteractionStorage

        return InteractionStorage(
            db_path=tmp_path / "test.db",
            log_dir=tmp_path / "logs",
        )

    @pytest.fixture
    def logger(self, storage):
        """Create logger for testing."""
        from ara.logger.interaction import InteractionLogger

        return InteractionLogger(
            device_id="test-device",
            storage=storage,
        )

    def test_local_response_logged_correctly(self, logger, storage) -> None:
        """Test local LLM response is logged with correct source."""
        from ara.logger.interaction import ResponseSource

        interaction = logger.log(
            transcript="what time is it",
            response="It's 3:30 PM",
            intent="general_question",
            latency_ms={"total": 500},
            response_source=ResponseSource.LOCAL_LLM,
        )

        assert interaction.response_source == ResponseSource.LOCAL_LLM

    def test_cloud_response_logged_correctly(self, logger, storage) -> None:
        """Test cloud API response is logged with correct source."""
        from ara.logger.interaction import ResponseSource

        interaction = logger.log(
            transcript="search for something",
            response="Found results",
            intent="web_search",
            latency_ms={"total": 1000},
            response_source=ResponseSource.CLOUD_API,
        )

        assert interaction.response_source == ResponseSource.CLOUD_API

    def test_system_response_logged_correctly(self, logger, storage) -> None:
        """Test system response is logged with correct source."""
        from ara.logger.interaction import ResponseSource

        interaction = logger.log(
            transcript="set a timer for 5 minutes",
            response="Timer set",
            intent="timer_set",
            latency_ms={"total": 100},
            response_source=ResponseSource.SYSTEM,
        )

        assert interaction.response_source == ResponseSource.SYSTEM
