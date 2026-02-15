import sys

import pygame

from pi_audio.audio import AudioCapture
from pi_audio.config import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from pi_audio.screens.meter import MeterScreen
from pi_audio.screens.settings import SettingsScreen
from pi_audio.settings import Settings


def main() -> None:
    pygame.init()
    pygame.mouse.set_visible(True)

    surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
    pygame.display.set_caption("pi-audio")
    clock = pygame.time.Clock()

    # Create settings and audio capture
    settings = Settings()
    audio = AudioCapture(history_length=settings.history_length)
    audio.start()

    # Track previous history length to detect changes
    prev_history_length = settings.history_length

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

            # Update audio history length if settings changed
            if settings.history_length != prev_history_length:
                audio.set_history_length(settings.history_length)
                prev_history_length = settings.history_length

            # Only update audio data for meter screen
            if isinstance(screen, MeterScreen):
                screen.set_audio_data(audio.current_spl, audio.history)

            screen.update(dt)
            screen.draw(surface)
            pygame.display.flip()

    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        audio.stop()
        pygame.quit()
        sys.exit(0)
