import json
from pathlib import Path

_SETTINGS_PATH = Path.home() / ".config" / "pi-audio" / "settings.json"

_KEYS = (
    "history_seconds",
    "quiet_threshold",
    "moderate_threshold",
    "display_mode",
    "overtone_freq_min",
    "overtone_freq_max",
)


class Settings:
    """Application settings that can be customized by the user."""

    def __init__(self):
        # History length in seconds (5 seconds to 5 minutes)
        self.history_seconds: int = 30

        # Sound level thresholds in dB(A)
        self.quiet_threshold: float = 75.0  # Safe/green zone upper limit
        self.moderate_threshold: float = 90.0  # Cautious/yellow zone upper limit

        # Display mode: "meter", "overtones", or "both"
        self.display_mode: str = "both"

        # Overtone frequency range in Hz (allowed: 40–8000)
        self.overtone_freq_min: int = 100
        self.overtone_freq_max: int = 4000

        self._load()

    @property
    def history_length(self) -> int:
        """Number of history samples based on history_seconds."""
        from pi_audio.config import BLOCK_SIZE, SAMPLE_RATE

        return self.history_seconds * (SAMPLE_RATE // BLOCK_SIZE)

    def validate_and_clamp(self) -> None:
        """Ensure settings are within valid ranges."""
        # History: 5 seconds to 5 minutes
        self.history_seconds = max(5, min(300, self.history_seconds))

        # Thresholds: keep within reasonable SPL range (20-100 dB)
        # and ensure quiet < moderate
        self.quiet_threshold = max(40.0, min(95.0, self.quiet_threshold))
        self.moderate_threshold = max(
            max(60.0, self.quiet_threshold + 1.0), min(100.0, self.moderate_threshold)
        )

        # Display mode
        if self.display_mode not in ("meter", "overtones", "both", "value_only"):
            self.display_mode = "both"

        # Overtone frequency range: 40–8000 Hz, min < max
        self.overtone_freq_min = max(40, min(7999, self.overtone_freq_min))
        self.overtone_freq_max = max(self.overtone_freq_min + 1, min(8000, self.overtone_freq_max))

    def save(self) -> None:
        """Persist current settings to disk."""
        data = {k: getattr(self, k) for k in _KEYS}
        try:
            _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            _SETTINGS_PATH.write_text(json.dumps(data, indent=2) + "\n")
        except OSError:
            pass

    def _load(self) -> None:
        """Load settings from disk if available."""
        try:
            data = json.loads(_SETTINGS_PATH.read_text())
            for k in _KEYS:
                if k in data:
                    setattr(self, k, type(getattr(self, k))(data[k]))
            self.validate_and_clamp()
        except (OSError, json.JSONDecodeError, ValueError):
            pass
