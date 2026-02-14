import collections
import threading

import numpy as np
import sounddevice as sd
from scipy.signal import sosfilt, zpk2sos

from pi_audio.config import BLOCK_SIZE, HISTORY_LENGTH, SAMPLE_RATE


def _a_weighting_sos(fs: int) -> np.ndarray:
    """Design an A-weighting filter as second-order sections.

    Based on IEC 61672:2003 analog prototype, bilinear-transformed to digital.
    """
    # Analog A-weighting pole/zero frequencies
    f1 = 20.598997
    f2 = 107.65265
    f3 = 737.86223
    f4 = 12194.217

    # Analog zeros and poles (in rad/s)
    zeros = [0, 0, 0, 0]
    poles = [
        -2 * np.pi * f1,
        -2 * np.pi * f1,
        -2 * np.pi * f2,
        -2 * np.pi * f3,
        -2 * np.pi * f4,
        -2 * np.pi * f4,
    ]

    # Bilinear transform: s = 2*fs*(z-1)/(z+1)
    # Pre-warp is not needed for A-weighting since we normalize gain at 1 kHz
    z_d = []
    p_d = []

    for p in poles:
        p_d.append((1 + p / (2 * fs)) / (1 - p / (2 * fs)))
    for z in zeros:
        z_d.append((1 + z / (2 * fs)) / (1 - z / (2 * fs)))

    # Add zeros at z = -1 (Nyquist) to match order
    while len(z_d) < len(p_d):
        z_d.append(-1.0)

    z_d = np.array(z_d)
    p_d = np.array(p_d)

    # Compute gain: normalize so that |H(f=1000)| = 1 (0 dB at 1 kHz)
    w = 2 * np.pi * 1000 / fs
    ejw = np.exp(1j * w)

    num = np.prod(ejw - z_d)
    den = np.prod(ejw - p_d)
    k = 1.0 / np.abs(num / den)

    sos = zpk2sos(z_d, p_d, k)
    return sos


class AudioCapture:
    def __init__(self, sample_rate: int = SAMPLE_RATE, block_size: int = BLOCK_SIZE):
        self.sample_rate = sample_rate
        self.block_size = block_size
        self._sos = _a_weighting_sos(sample_rate)
        self._current_spl: float = 0.0
        self._history: collections.deque[float] = collections.deque(maxlen=HISTORY_LENGTH)
        self._lock = threading.Lock()
        self._stream: sd.InputStream | None = None

    def _callback(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            pass  # drop-outs are expected occasionally
        audio = indata[:, 0].astype(np.float64)
        filtered = sosfilt(self._sos, audio)
        rms = np.sqrt(np.mean(filtered**2))

        # Convert to dB SPL (reference: full-scale = ~94 dB SPL for typical USB mics)
        # Using a relative reference — actual calibration would need a known source
        if rms > 0:
            db = 20 * np.log10(rms) + 94.0
        else:
            db = 0.0

        with self._lock:
            self._current_spl = db
            self._history.append(db)

    @property
    def current_spl(self) -> float:
        with self._lock:
            return self._current_spl

    @property
    def history(self) -> list[float]:
        with self._lock:
            return list(self._history)

    def start(self) -> None:
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            blocksize=self.block_size,
            channels=1,
            dtype="float32",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
