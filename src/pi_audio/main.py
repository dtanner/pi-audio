import sys

import pygame

from pi_audio.audio import AudioCapture
from pi_audio.config import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from pi_audio.screens.meter import MeterScreen
from pi_audio.screens.settings import SettingsScreen
from pi_audio.settings import Settings


def main() -> None:
    import os

    windowed = "--windowed" in sys.argv or os.environ.get("PI_AUDIO_WINDOWED") == "1"

    pygame.init()
    pygame.mouse.set_visible(True)

    flags = 0 if windowed else pygame.FULLSCREEN
    surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
    pygame.display.set_caption("pi-audio")
    clock = pygame.time.Clock()

    # Create settings and audio capture
    settings = Settings()
    audio = AudioCapture(history_length=settings.history_length)
    audio.set_pitch_range(settings.pitch_note_min, settings.pitch_note_max)
    audio.start()

    # Track previous settings to detect changes
    prev_history_length = settings.history_length
    prev_pitch_range = (settings.pitch_note_min, settings.pitch_note_max)

    # Screen management
    current_screen_name = "meter"

    def switch_to_settings() -> None:
        nonlocal current_screen_name
        current_screen_name = "settings"

    def switch_to_meter() -> None:
        nonlocal current_screen_name
        current_screen_name = "meter"

    meter_screen = MeterScreen(settings, on_settings=switch_to_settings)
    settings_screen = SettingsScreen(settings, on_back=switch_to_meter)

    try:
        while True:
            dt = clock.tick(FPS) / 1000.0

            # Get current screen
            screen = meter_screen if current_screen_name == "meter" else settings_screen

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    raise SystemExit
                screen.handle_event(event)

            # Update audio settings if changed
            if settings.history_length != prev_history_length:
                audio.set_history_length(settings.history_length)
                prev_history_length = settings.history_length
            pitch_range = (settings.pitch_note_min, settings.pitch_note_max)
            if pitch_range != prev_pitch_range:
                audio.set_pitch_range(*pitch_range)
                prev_pitch_range = pitch_range

            # Only update audio data for meter screen
            if isinstance(screen, MeterScreen):
                panels = settings.active_panels
                spec = audio.spectrogram if "overtones" in panels else None
                pitch = audio.current_pitch
                pitch_hist = audio.pitch_history if "pitch" in panels else None
                screen.set_audio_data(audio.current_spl, audio.history, spec, pitch, pitch_hist)

            screen.update(dt)
            screen.draw(surface)
            pygame.display.flip()

    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        audio.stop()
        pygame.quit()
        sys.exit(0)
