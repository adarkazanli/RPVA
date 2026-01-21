"""macOS TTS synthesizer using native `say` command.

Provides high-quality speech synthesis using macOS's built-in TTS.
"""

import logging
import shutil
import subprocess
import tempfile
import time
import wave
from pathlib import Path

from .synthesizer import SynthesisResult

logger = logging.getLogger(__name__)


class MacOSSynthesizer:
    """Text-to-speech synthesizer using macOS native `say` command.

    Uses the system TTS with the "Samantha" voice by default,
    providing high-quality speech output on macOS.
    """

    # Target sample rate to match Piper output
    TARGET_SAMPLE_RATE = 22050

    def __init__(self, voice: str = "Samantha", speed: float = 1.0) -> None:
        """Initialize macOS synthesizer.

        Args:
            voice: Voice name (default: "Samantha")
            speed: Speech speed multiplier (default: 1.0)
        """
        self._voice = voice
        self._speed = max(0.5, min(2.0, speed))
        self._say_path = shutil.which("say")

    @property
    def is_available(self) -> bool:
        """Check if macOS TTS is available.

        Returns:
            True if the `say` command is available.
        """
        return self._say_path is not None

    def synthesize(self, text: str) -> SynthesisResult:
        """Convert text to speech audio.

        Args:
            text: Text to synthesize

        Returns:
            SynthesisResult with PCM audio data

        Raises:
            RuntimeError: If synthesis fails
        """
        start_time = time.time()

        if not self.is_available:
            raise RuntimeError("macOS TTS not available: say command not found")

        try:
            # Create temp file for AIFF output
            with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as f:
                temp_aiff = Path(f.name)

            try:
                # Run say command
                self._run_say_command(text, temp_aiff)

                # Convert AIFF to PCM
                audio_data, sample_rate = self._convert_aiff_to_pcm(temp_aiff)

                # Calculate duration from audio data
                # 16-bit audio = 2 bytes per sample
                duration_ms = int(len(audio_data) / (sample_rate * 2) * 1000)
                latency_ms = int((time.time() - start_time) * 1000)

                logger.debug(
                    f"Synthesized '{text[:30]}...' in {latency_ms}ms ({duration_ms}ms audio)"
                )

                return SynthesisResult(
                    audio=audio_data,
                    sample_rate=sample_rate,
                    duration_ms=max(1, duration_ms),
                    latency_ms=latency_ms,
                )
            finally:
                # Clean up temp file
                if temp_aiff.exists():
                    temp_aiff.unlink()

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"macOS TTS synthesis failed: {e}") from e
        except Exception as e:
            raise RuntimeError(f"macOS TTS synthesis failed: {e}") from e

    def _run_say_command(self, text: str, output_path: Path) -> None:
        """Run the macOS say command to generate AIFF audio.

        Args:
            text: Text to synthesize
            output_path: Path to write AIFF output
        """
        # Calculate rate: say uses words per minute, default ~175
        # Speed 1.0 = 175 wpm, 0.5 = 87.5 wpm, 2.0 = 350 wpm
        rate = int(175 * self._speed)

        cmd = [
            "say",
            "-v",
            self._voice,
            "-r",
            str(rate),
            "-o",
            str(output_path),
            text or " ",  # Use space for empty text to avoid errors
        ]

        subprocess.run(cmd, check=True, capture_output=True, timeout=30)

    def _convert_aiff_to_pcm(self, aiff_path: Path) -> tuple[bytes, int]:
        """Convert AIFF file to 16-bit PCM bytes.

        Args:
            aiff_path: Path to AIFF file

        Returns:
            Tuple of (pcm_bytes, sample_rate)
        """
        # Use afconvert to convert to 16-bit signed integer WAV
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_wav = Path(f.name)

        try:
            # afconvert is macOS built-in
            subprocess.run(
                [
                    "afconvert",
                    "-f",
                    "WAVE",
                    "-d",
                    "LEI16",  # Little-endian 16-bit integer
                    "-r",
                    str(self.TARGET_SAMPLE_RATE),
                    str(aiff_path),
                    str(temp_wav),
                ],
                check=True,
                capture_output=True,
                timeout=30,
            )

            # Read WAV file and extract PCM data
            with wave.open(str(temp_wav), "rb") as wav_file:
                sample_rate = wav_file.getframerate()
                audio_data = wav_file.readframes(wav_file.getnframes())

            return audio_data, sample_rate

        finally:
            if temp_wav.exists():
                temp_wav.unlink()

    def set_voice(self, voice_id: str) -> None:
        """Set the voice for synthesis.

        Args:
            voice_id: Voice name (e.g., "Samantha", "Alex")
        """
        self._voice = voice_id

    def set_speed(self, speed: float) -> None:
        """Set speech speed multiplier.

        Args:
            speed: Speed multiplier (0.5 to 2.0, 1.0 = normal)
        """
        self._speed = max(0.5, min(2.0, speed))

    def get_available_voices(self) -> list[str]:
        """List available macOS voices.

        Returns:
            List of voice names available on this system.
        """
        if not self.is_available:
            return []

        try:
            result = subprocess.run(
                ["say", "-v", "?"],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )

            voices = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    # Format: "Samantha            en_US    # Hello..."
                    # Extract voice name (first whitespace-separated word)
                    parts = line.split()
                    if parts:
                        voices.append(parts[0])

            return voices

        except Exception:
            logger.warning("Failed to list macOS voices")
            return []


__all__ = ["MacOSSynthesizer"]
