"""Monophonic pitch detection using the YIN algorithm."""

import math

import numpy as np


def yin_pitch(
    audio_block: np.ndarray,
    sample_rate: int,
    threshold: float = 0.15,
) -> float | None:
    """Detect the fundamental frequency of a monophonic audio block.

    Uses the YIN autocorrelation method.

    Returns the detected frequency in Hz, or None if no clear pitch is found
    (aperiodic noise, silence, or low confidence).
    """
    n = len(audio_block)
    if n < 2:
        return None

    # RMS silence gate — skip very quiet signals
    rms = np.sqrt(np.mean(audio_block**2))
    if rms < 1e-4:
        return None

    # YIN operates on the first half of the block
    tau_max = n // 2

    # Step 1 & 2: Difference function + cumulative mean normalized difference
    # Using an efficient FFT-based difference function
    d = _difference_function(audio_block, tau_max)
    d_prime = _cumulative_mean_normalized_difference(d)

    # Step 3: Absolute threshold — find the first dip below threshold
    tau = _absolute_threshold(d_prime, threshold)
    if tau is None:
        return None

    # Step 4: Parabolic interpolation for sub-sample accuracy
    tau_refined = _parabolic_interpolation(d_prime, tau)

    if tau_refined <= 0:
        return None

    freq = sample_rate / tau_refined

    # Sanity check: reject implausible musical frequencies
    if freq < 30.0 or freq > 5000.0:
        return None

    return freq


def _difference_function(audio: np.ndarray, tau_max: int) -> np.ndarray:
    """Compute the YIN difference function using FFT for efficiency."""
    n = len(audio)
    # Pad to next power of 2 for FFT efficiency
    fft_size = 1
    while fft_size < n:
        fft_size <<= 1
    fft_size <<= 1  # double for autocorrelation

    # Autocorrelation via FFT
    audio_padded = np.zeros(fft_size)
    audio_padded[:n] = audio
    fft_audio = np.fft.rfft(audio_padded)
    acf = np.fft.irfft(fft_audio * np.conj(fft_audio))

    # Energy terms
    # d(tau) = r(0) + r_shifted(0) - 2*acf(tau)
    # r(0) = sum of x[j]^2 for j in [0, W)
    # r_shifted(tau) = sum of x[j+tau]^2 for j in [0, W)
    w = tau_max
    x_sq = audio[:n] ** 2
    # Cumulative sum for efficient energy computation
    cum = np.concatenate(([0.0], np.cumsum(x_sq)))

    energy_start = cum[w] - cum[0]  # sum of x[0..W-1]^2

    d = np.zeros(tau_max)
    d[0] = 0.0
    for tau in range(1, tau_max):
        energy_shifted = cum[w + tau] - cum[tau]  # sum of x[tau..tau+W-1]^2
        d[tau] = energy_start + energy_shifted - 2.0 * acf[tau]

    return d


def _cumulative_mean_normalized_difference(d: np.ndarray) -> np.ndarray:
    """Normalize the difference function (step 2 of YIN)."""
    n = len(d)
    d_prime = np.ones(n)
    cumulative = 0.0
    for tau in range(1, n):
        cumulative += d[tau]
        if cumulative > 0:
            d_prime[tau] = d[tau] * tau / cumulative
        else:
            d_prime[tau] = 1.0
    return d_prime


def _absolute_threshold(d_prime: np.ndarray, threshold: float) -> int | None:
    """Find the first lag below threshold that is a local minimum."""
    n = len(d_prime)
    # Skip tau=0, start searching from a reasonable minimum period
    # (corresponds to ~5000 Hz at 48kHz sample rate)
    for tau in range(2, n):
        if d_prime[tau] < threshold:
            # Walk forward to find the local minimum
            while tau + 1 < n and d_prime[tau + 1] < d_prime[tau]:
                tau += 1
            return tau
    return None


def _parabolic_interpolation(d_prime: np.ndarray, tau: int) -> float:
    """Refine the lag estimate using parabolic interpolation."""
    if tau <= 0 or tau >= len(d_prime) - 1:
        return float(tau)

    s0 = d_prime[tau - 1]
    s1 = d_prime[tau]
    s2 = d_prime[tau + 1]

    denom = 2.0 * (2.0 * s1 - s2 - s0)
    if abs(denom) < 1e-10:
        return float(tau)

    adjustment = (s2 - s0) / denom
    return tau + adjustment


def freq_to_note(freq_hz: float) -> tuple[str, int, int]:
    """Convert a frequency in Hz to the nearest musical note.

    Returns (note_name, octave, cents_offset) where cents_offset is in [-50, +49].
    For example: ("A", 4, -12) means 12 cents flat of A4.
    """
    _NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

    # Semitones from A4 (440 Hz)
    semitones_from_a4 = 12.0 * math.log2(freq_hz / 440.0)

    # Round to nearest semitone
    nearest_semitone = round(semitones_from_a4)
    cents = round((semitones_from_a4 - nearest_semitone) * 100.0)

    # A4 is MIDI note 69, which is index 9 in the octave (0=C)
    midi_note = 69 + nearest_semitone
    note_index = midi_note % 12
    octave = midi_note // 12 - 1  # MIDI octave convention

    note_name = _NOTE_NAMES[note_index]
    return note_name, octave, cents
