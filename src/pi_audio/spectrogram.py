import numpy as np
import pygame

from pi_audio.config import SPEC_DB_MAX, SPEC_DB_MIN, SPEC_FREQ_MAX, SPEC_FREQ_MIN


def _build_color_lut() -> np.ndarray:
    """Build a 256-entry RGB color lookup table: dark blue → blue → cyan → yellow → red."""
    lut = np.zeros((256, 3), dtype=np.uint8)
    # 5 stops: dark-blue(0), blue(64), cyan(128), yellow(192), red(255)
    stops = [
        (0, (10, 10, 40)),
        (64, (20, 20, 180)),
        (128, (0, 200, 220)),
        (192, (240, 220, 0)),
        (255, (240, 50, 30)),
    ]
    for i in range(len(stops) - 1):
        idx0, c0 = stops[i]
        idx1, c1 = stops[i + 1]
        for j in range(idx0, idx1 + 1):
            t = (j - idx0) / max(idx1 - idx0, 1)
            for ch in range(3):
                lut[j, ch] = int(c0[ch] + t * (c1[ch] - c0[ch]))
    return lut


class SpectrogramRenderer:
    def __init__(
        self,
        sample_rate: int,
        block_size: int,
        freq_min: float = SPEC_FREQ_MIN,
        freq_max: float = SPEC_FREQ_MAX,
    ):
        self._sample_rate = sample_rate
        self._block_size = block_size
        self._freq_min = freq_min
        self._freq_max = freq_max
        self._color_lut = _build_color_lut()

        # Precompute FFT bin frequencies
        self._bin_freqs = np.fft.rfftfreq(block_size, 1.0 / sample_rate)

        # We'll lazily build the row→bin mapping when we know the display height
        self._cached_height: int = 0
        self._row_bin_indices: np.ndarray = np.array([])

        self._font: pygame.font.Font | None = None

    def _ensure_font(self) -> None:
        if self._font is None:
            self._font = pygame.font.SysFont("monospace", 14)

    def _build_row_mapping(self, height: int) -> None:
        """Map each display row to an FFT bin index using logarithmic frequency scale."""
        if height == self._cached_height:
            return
        self._cached_height = height

        log_min = np.log10(self._freq_min)
        log_max = np.log10(self._freq_max)
        # Row 0 = top = highest freq, row height-1 = bottom = lowest freq
        log_freqs = np.linspace(log_max, log_min, height)
        freqs = 10.0**log_freqs

        # Find closest FFT bin for each row
        bin_resolution = self._sample_rate / self._block_size
        self._row_bin_indices = np.clip(
            np.round(freqs / bin_resolution).astype(int),
            0,
            self._block_size // 2,
        )

    def _db_to_color_index(self, db_values: np.ndarray) -> np.ndarray:
        """Map dB values to 0..255 color indices."""
        normalized = (db_values - SPEC_DB_MIN) / (SPEC_DB_MAX - SPEC_DB_MIN)
        return np.clip(normalized * 255, 0, 255).astype(np.uint8)

    def draw(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        spectrogram_data: list[np.ndarray],
    ) -> None:
        self._ensure_font()
        self._build_row_mapping(rect.height)

        width = rect.width
        height = rect.height

        # Build pixel array (height x width x 3)
        pixels = np.zeros((height, width, 3), dtype=np.uint8)
        # Fill with background color
        pixels[:, :] = self._color_lut[0]

        n_cols = len(spectrogram_data)
        if n_cols > 0:
            if n_cols >= width:
                # More data than pixels: show the most recent `width` columns
                visible = spectrogram_data[n_cols - width :]
                for col_idx, mag_db in enumerate(visible):
                    row_values = mag_db[self._row_bin_indices]
                    color_indices = self._db_to_color_index(row_values)
                    pixels[:, col_idx] = self._color_lut[color_indices]
            else:
                # Fewer data points than pixels: stretch to fill the width
                for px in range(width):
                    # Map pixel to data index (right-aligned, most recent at right)
                    data_idx = int(px * n_cols / width)
                    data_idx = min(data_idx, n_cols - 1)
                    mag_db = spectrogram_data[data_idx]
                    row_values = mag_db[self._row_bin_indices]
                    color_indices = self._db_to_color_index(row_values)
                    pixels[:, px] = self._color_lut[color_indices]

        # Transpose to (width, height, 3) for pygame surfarray
        pixel_surf = pygame.surfarray.make_surface(pixels.transpose(1, 0, 2))
        surface.blit(pixel_surf, (rect.x, rect.y))

        # Frequency axis labels at octave-ish intervals
        label_freqs = [100, 200, 500, 1000, 2000, 4000, 8000]
        log_min = np.log10(self._freq_min)
        log_max = np.log10(self._freq_max)
        for freq in label_freqs:
            if freq < self._freq_min or freq > self._freq_max:
                continue
            frac = (np.log10(freq) - log_min) / (log_max - log_min)
            y = rect.y + int((1.0 - frac) * rect.height)
            if freq >= 1000:
                text = f"{freq // 1000}k"
            else:
                text = str(freq)
            label = self._font.render(text, True, (180, 180, 200))
            lx = rect.x + 4
            ly = y - label.get_height() // 2
            # Clamp to rect bounds
            ly = max(rect.y, min(rect.y + rect.height - label.get_height(), ly))
            surface.blit(label, (lx, ly))
            # Tick mark
            pygame.draw.line(surface, (80, 80, 100), (rect.x, y), (rect.x + 3, y))
