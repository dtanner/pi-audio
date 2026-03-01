"""Tests for YIN pitch detection accuracy."""

import numpy as np
import pytest

from pi_audio.pitch import freq_to_note, yin_pitch

SAMPLE_RATE = 48000
BLOCK_SIZE = 4800  # 100ms


def _tone(freq_hz: float, amplitude: float = 0.5) -> np.ndarray:
    """Generate a pure sine tone at the given frequency."""
    t = np.arange(BLOCK_SIZE) / SAMPLE_RATE
    return amplitude * np.sin(2 * np.pi * freq_hz * t)


class TestYinPitchAccuracy:
    """Verify that yin_pitch detects known frequencies within ±5 cents."""

    @pytest.mark.parametrize(
        "freq_hz, expected_note, expected_octave",
        [
            (261.63, "C", 4),
            (329.63, "E", 4),
            (440.00, "A", 4),
            (523.25, "C", 5),
            (880.00, "A", 5),
        ],
    )
    def test_pure_tone_accuracy(self, freq_hz, expected_note, expected_octave):
        tone = _tone(freq_hz)
        detected = yin_pitch(tone, SAMPLE_RATE)
        assert detected is not None, f"Failed to detect {freq_hz} Hz"

        note, octave, cents = freq_to_note(detected)
        assert note == expected_note
        assert octave == expected_octave
        assert abs(cents) <= 5, (
            f"{freq_hz} Hz: expected ≤5 cents error, got {cents} cents "
            f"(detected {detected:.2f} Hz)"
        )

    def test_a440_near_exact(self):
        """A 440 Hz tone should be detected within ±1 cent."""
        tone = _tone(440.0)
        detected = yin_pitch(tone, SAMPLE_RATE)
        assert detected is not None
        _, _, cents = freq_to_note(detected)
        assert abs(cents) <= 1, f"A440: expected ≤1 cent error, got {cents} cents"

    def test_silence_returns_none(self):
        silence = np.zeros(BLOCK_SIZE)
        assert yin_pitch(silence, SAMPLE_RATE) is None

    def test_noise_returns_none(self):
        rng = np.random.default_rng(42)
        noise = rng.normal(0, 0.01, BLOCK_SIZE)
        assert yin_pitch(noise, SAMPLE_RATE) is None

    def test_low_amplitude_tone(self):
        """A very quiet but non-silent tone should still be detected."""
        tone = _tone(440.0, amplitude=0.001)
        detected = yin_pitch(tone, SAMPLE_RATE)
        assert detected is not None
        _, _, cents = freq_to_note(detected)
        assert abs(cents) <= 5


class TestFreqToNote:
    def test_a440(self):
        note, octave, cents = freq_to_note(440.0)
        assert (note, octave, cents) == ("A", 4, 0)

    def test_c4(self):
        note, octave, cents = freq_to_note(261.626)
        assert note == "C"
        assert octave == 4
        assert abs(cents) <= 1

    def test_sharp_and_flat(self):
        # 10 cents sharp of A4
        note, octave, cents = freq_to_note(440.0 * 2 ** (10 / 1200))
        assert (note, octave, cents) == ("A", 4, 10)

        # 10 cents flat of A4
        note, octave, cents = freq_to_note(440.0 * 2 ** (-10 / 1200))
        assert (note, octave, cents) == ("A", 4, -10)
