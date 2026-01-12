#!/usr/bin/env python3
"""Generate test audio fixtures for Ara Voice Assistant.

Creates WAV files for feedback sounds (beeps, chimes, etc.)
and test audio samples.
"""

import math
import struct
import wave
from pathlib import Path


def generate_sine_wave(
    frequency: int,
    duration_ms: int,
    sample_rate: int = 22050,
    amplitude: float = 0.5,
) -> bytes:
    """Generate a sine wave with envelope."""
    num_samples = int(sample_rate * duration_ms / 1000)
    audio_data = []

    for i in range(num_samples):
        t = i / sample_rate

        # Apply attack/release envelope
        envelope = 1.0
        attack_samples = int(sample_rate * 0.01)
        release_samples = int(sample_rate * 0.02)

        if i < attack_samples:
            envelope = i / attack_samples
        elif i > num_samples - release_samples:
            envelope = (num_samples - i) / release_samples

        sample = int(32767 * amplitude * envelope * math.sin(2 * math.pi * frequency * t))
        audio_data.append(struct.pack("<h", sample))

    return b"".join(audio_data)


def generate_dual_tone(
    freq1: int,
    freq2: int,
    duration_ms: int,
    sample_rate: int = 22050,
) -> bytes:
    """Generate a dual-tone sound (like DTMF)."""
    num_samples = int(sample_rate * duration_ms / 1000)
    audio_data = []

    for i in range(num_samples):
        t = i / sample_rate
        envelope = 1.0
        attack_samples = int(sample_rate * 0.01)
        release_samples = int(sample_rate * 0.02)

        if i < attack_samples:
            envelope = i / attack_samples
        elif i > num_samples - release_samples:
            envelope = (num_samples - i) / release_samples

        sample = int(
            32767
            * 0.3
            * envelope
            * (math.sin(2 * math.pi * freq1 * t) + math.sin(2 * math.pi * freq2 * t))
        )
        audio_data.append(struct.pack("<h", sample))

    return b"".join(audio_data)


def generate_chime(duration_ms: int = 300, sample_rate: int = 22050) -> bytes:
    """Generate a pleasant chime sound."""
    num_samples = int(sample_rate * duration_ms / 1000)
    audio_data = []

    # Chime uses multiple harmonics
    frequencies = [523, 659, 784]  # C5, E5, G5 - C major chord

    for i in range(num_samples):
        t = i / sample_rate

        # Exponential decay envelope
        envelope = math.exp(-3 * t / (duration_ms / 1000))

        sample_value = 0.0
        for j, freq in enumerate(frequencies):
            # Each harmonic decays at different rate
            harmonic_env = math.exp(-(3 + j) * t / (duration_ms / 1000))
            sample_value += harmonic_env * math.sin(2 * math.pi * freq * t)

        sample = int(32767 * 0.25 * envelope * sample_value)
        sample = max(-32767, min(32767, sample))
        audio_data.append(struct.pack("<h", sample))

    return b"".join(audio_data)


def generate_error_sound(duration_ms: int = 300, sample_rate: int = 22050) -> bytes:
    """Generate an error sound (low descending tones)."""
    num_samples = int(sample_rate * duration_ms / 1000)
    audio_data = []

    for i in range(num_samples):
        t = i / sample_rate
        progress = i / num_samples

        # Descending frequency
        freq = 400 - 150 * progress

        # Envelope
        envelope = 1.0 - 0.5 * progress
        if i < sample_rate * 0.01:
            envelope *= i / (sample_rate * 0.01)

        sample = int(32767 * 0.4 * envelope * math.sin(2 * math.pi * freq * t))
        audio_data.append(struct.pack("<h", sample))

    return b"".join(audio_data)


def generate_alarm(duration_ms: int = 500, sample_rate: int = 22050) -> bytes:
    """Generate an alarm sound (alternating tones)."""
    num_samples = int(sample_rate * duration_ms / 1000)
    audio_data = []

    # Alternate between two frequencies
    freq1, freq2 = 800, 1000
    switch_rate = 8  # Hz

    for i in range(num_samples):
        t = i / sample_rate

        # Switch frequency based on time
        freq = freq1 if int(t * switch_rate) % 2 == 0 else freq2

        # Envelope
        envelope = 0.6
        attack_samples = int(sample_rate * 0.01)
        release_samples = int(sample_rate * 0.02)

        if i < attack_samples:
            envelope *= i / attack_samples
        elif i > num_samples - release_samples:
            envelope *= (num_samples - i) / release_samples

        sample = int(32767 * envelope * math.sin(2 * math.pi * freq * t))
        audio_data.append(struct.pack("<h", sample))

    return b"".join(audio_data)


def generate_success_sound(duration_ms: int = 200, sample_rate: int = 22050) -> bytes:
    """Generate a success sound (ascending tones)."""
    num_samples = int(sample_rate * duration_ms / 1000)
    audio_data = []

    for i in range(num_samples):
        t = i / sample_rate
        progress = i / num_samples

        # Ascending frequency
        freq = 400 + 200 * progress

        # Envelope with longer release
        envelope = 1.0
        attack_samples = int(sample_rate * 0.02)
        release_samples = int(sample_rate * 0.05)

        if i < attack_samples:
            envelope = i / attack_samples
        elif i > num_samples - release_samples:
            envelope = (num_samples - i) / release_samples

        sample = int(32767 * 0.4 * envelope * math.sin(2 * math.pi * freq * t))
        audio_data.append(struct.pack("<h", sample))

    return b"".join(audio_data)


def save_wav(audio_data: bytes, path: Path, sample_rate: int = 22050) -> None:
    """Save audio data as WAV file."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_data)


def main() -> None:
    """Generate all test audio fixtures."""
    # Output directories
    fixtures_dir = Path(__file__).parent.parent / "tests" / "fixtures" / "audio"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    sample_rate = 22050

    # Generate feedback sounds
    sounds = {
        "beep.wav": generate_sine_wave(880, 100, sample_rate),
        "error.wav": generate_error_sound(300, sample_rate),
        "chime.wav": generate_chime(300, sample_rate),
        "alarm.wav": generate_alarm(500, sample_rate),
        "success.wav": generate_success_sound(200, sample_rate),
    }

    for filename, audio_data in sounds.items():
        path = fixtures_dir / filename
        save_wav(audio_data, path, sample_rate)
        print(f"Created: {path}")

    # Generate test speech sample (silence with some tone for now)
    # In real testing, you'd record actual speech samples
    test_speech = generate_sine_wave(440, 1000, 16000, amplitude=0.1)
    test_speech_path = fixtures_dir / "test_speech.wav"
    save_wav(test_speech, test_speech_path, 16000)
    print(f"Created: {test_speech_path}")

    print("\nAll audio fixtures generated successfully!")


if __name__ == "__main__":
    main()
