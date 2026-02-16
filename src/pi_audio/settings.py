import json
from pathlib import Path

_SETTINGS_PATH = Path.home() / ".config" / "pi-audio" / "settings.json"

_KEYS = (
    "history_seconds",
    "quiet_threshold",
    "moderate_threshold",
    "active_panels",
    "overtone_freq_min",
    "overtone_freq_max",
    "pitch_note_min",
    "pitch_note_max",
    "pitch_range_auto",
)

_VALID_PANELS = ("overtones", "meter", "pitch")


class Settings:
    """Application settings that can be customized by the user."""

    def __init__(self):
        # History length in seconds (5 seconds to 5 minutes)
        self.history_seconds: int = 30

        # Sound level thresholds in dB(A)
        self.quiet_threshold: float = 75.0  # Safe/green zone upper limit
        self.moderate_threshold: float = 90.0  # Cautious/yellow zone upper limit

        # Active display panels: ordered list of up to 2 from ["overtones", "meter", "pitch"]
        self.active_panels: list[str] = ["overtones", "meter"]

        # Overtone frequency range in Hz (allowed: 40–8000)
        self.overtone_freq_min: int = 100
        self.overtone_freq_max: int = 4000

        # Pitch detection range as semitones from A4 (allowed: -39 to +39, i.e. C1 to D#8)
        # Default: E2 (-29) to G5 (+10)
        self.pitch_note_min: int = -29
        self.pitch_note_max: int = 10

        # Pitch chart range mode: True = auto-adjust to recent pitches, False = fixed to note range
        self.pitch_range_auto: bool = True

        self._load()

    @property
    def display_mode(self) -> str:
        """Derived display_mode for backward compatibility."""
        panels = set(self.active_panels)
        if panels == {"overtones", "meter"}:
            return "both"
        elif panels == {"overtones"}:
            return "overtones"
        elif panels == {"meter"}:
            return "meter"
        elif len(panels) == 0:
            return "value_only"
        # For any other combination (involving pitch), return a generic mode
        if len(panels) == 2:
            return "dual"
        return self.active_panels[0]

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

        # Active panels: max 2, only valid names, preserve order
        self.active_panels = [p for p in self.active_panels if p in _VALID_PANELS]
        # Remove duplicates while preserving order
        seen = set()
        deduped = []
        for p in self.active_panels:
            if p not in seen:
                seen.add(p)
                deduped.append(p)
        self.active_panels = deduped[:2]

        # Overtone frequency range: 40–8000 Hz, min < max
        self.overtone_freq_min = max(40, min(7999, self.overtone_freq_min))
        self.overtone_freq_max = max(self.overtone_freq_min + 1, min(8000, self.overtone_freq_max))

        # Pitch note range: -39 to +39 semitones from A4, min < max
        self.pitch_note_min = max(-39, min(38, self.pitch_note_min))
        self.pitch_note_max = max(self.pitch_note_min + 1, min(39, self.pitch_note_max))

    def save(self) -> None:
        """Persist current settings to disk."""
        data = {}
        for k in _KEYS:
            data[k] = getattr(self, k)
        try:
            _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            _SETTINGS_PATH.write_text(json.dumps(data, indent=2) + "\n")
        except OSError:
            pass

    def _load(self) -> None:
        """Load settings from disk if available."""
        try:
            data = json.loads(_SETTINGS_PATH.read_text())

            # Backward compatibility: convert old display_mode to active_panels
            if "display_mode" in data and "active_panels" not in data:
                old_mode = data.pop("display_mode")
                if old_mode == "both":
                    data["active_panels"] = ["overtones", "meter"]
                elif old_mode == "overtones":
                    data["active_panels"] = ["overtones"]
                elif old_mode == "meter":
                    data["active_panels"] = ["meter"]
                elif old_mode == "value_only":
                    data["active_panels"] = []
                # else: keep default

            for k in _KEYS:
                if k in data:
                    val = data[k]
                    default = getattr(self, k)
                    if isinstance(default, list):
                        if isinstance(val, list):
                            setattr(self, k, val)
                    else:
                        setattr(self, k, type(default)(val))
            self.validate_and_clamp()
        except (OSError, json.JSONDecodeError, ValueError):
            pass
