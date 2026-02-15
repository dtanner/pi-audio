import sys

import pygame

from pi_audio.audio import AudioCapture
from pi_audio.config import FPS, SCREEN_HEIGHT, SCREEN_WIDTH
from pi_audio.screens.meter import MeterScreen


def main() -> None:
    pygame.init()
    pygame.mouse.set_visible(True)

    surface = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
    pygame.display.set_caption("pi-audio")
    clock = pygame.time.Clock()

    audio = AudioCapture()
    audio.start()

    screen = MeterScreen()

    try:
        while True:
            dt = clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise SystemExit
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    raise SystemExit
                screen.handle_event(event)

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
