class Settings:
    """Application settings that can be customized by the user."""

    def __init__(self):
        # History length in seconds (5 seconds to 5 minutes)
        self.history_seconds: int = 30

        # Sound level thresholds in dB(A)
        self.quiet_threshold: float = 75.0  # Safe/green zone upper limit
        self.moderate_threshold: float = 90.0  # Cautious/yellow zone upper limit

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
        self.quiet_threshold = max(20.0, min(95.0, self.quiet_threshold))
        self.moderate_threshold = max(
            self.quiet_threshold + 1.0, min(100.0, self.moderate_threshold)
        )
