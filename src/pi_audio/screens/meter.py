import pygame

from pi_audio.config import (
    COLOR_BG,
    COLOR_BUTTON_BG,
    COLOR_BUTTON_HOVER,
    COLOR_BUTTON_TEXT,
    COLOR_CHART_BG,
    COLOR_GREEN,
    COLOR_GRID,
    COLOR_RED,
    COLOR_TEXT,
    COLOR_YELLOW,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SPL_MAX,
    SPL_MIN,
)
from pi_audio.screens.base import Screen
from pi_audio.settings import Settings


class MeterScreen(Screen):
    # Layout
    READOUT_HEIGHT = 220
    CHART_MARGIN = 40
    CHART_LEFT = 80
    CHART_RIGHT = 30
    CHART_BOTTOM = 40

    # Button dimensions
    BUTTON_WIDTH = 120
    BUTTON_HEIGHT = 50
    BUTTON_MARGIN = 20
    BUTTON_SPACING = 10

    def __init__(self, settings: Settings, on_settings: callable):
        self.settings = settings
        self.on_settings = on_settings
        self._spl: float = 0.0
        self._history: list[float] = []
        self._font_large: pygame.font.Font | None = None
        self._font_medium: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None
        self._font_icon: pygame.font.Font | None = None
        self._exit_button_rect: pygame.Rect | None = None
        self._settings_button_rect: pygame.Rect | None = None
        self._hovered_button: str | None = None

    def _ensure_fonts(self) -> None:
        if self._font_large is None:
            self._font_large = pygame.font.SysFont("monospace", 120, bold=True)
            self._font_medium = pygame.font.SysFont("monospace", 28)
            self._font_small = pygame.font.SysFont("monospace", 18)
            # Use a font with good Unicode symbol support for the gear icon
            for name in ("dejavusans", "noto", "segoeui", "arial", None):
                try:
                    self._font_icon = pygame.font.SysFont(name, 32)
                    if self._font_icon.render("\u2699", True, (255, 255, 255)).get_width() > 5:
                        break
                except Exception:
                    continue

    def set_audio_data(self, spl: float, history: list[float]) -> None:
        self._spl = spl
        self._history = history

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hovered_button = None
            if self._exit_button_rect and self._exit_button_rect.collidepoint(event.pos):
                self._hovered_button = "exit"
            elif self._settings_button_rect and self._settings_button_rect.collidepoint(event.pos):
                self._hovered_button = "settings"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._exit_button_rect and self._exit_button_rect.collidepoint(event.pos):
                raise SystemExit
            elif self._settings_button_rect and self._settings_button_rect.collidepoint(event.pos):
                self.on_settings()

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        surface.fill(COLOR_BG)
        self._draw_readout(surface)
        self._draw_chart(surface)
        self._draw_buttons(surface)

    def _spl_color(self, db: float) -> tuple[int, int, int]:
        """Determine color based on SPL level and current thresholds."""
        if db < self.settings.quiet_threshold:
            return COLOR_GREEN
        elif db < self.settings.moderate_threshold:
            return COLOR_YELLOW
        else:
            return COLOR_RED

    def _draw_readout(self, surface: pygame.Surface) -> None:
        color = self._spl_color(self._spl)

        # Main number
        text = f"{self._spl:5.1f}"
        rendered = self._font_large.render(text, True, color)
        rect = rendered.get_rect(centerx=SCREEN_WIDTH // 2, centery=self.READOUT_HEIGHT // 2 - 10)
        surface.blit(rendered, rect)

        # Unit label
        label = self._font_medium.render("dB(A)", True, COLOR_TEXT)
        label_rect = label.get_rect(centerx=SCREEN_WIDTH // 2, top=rect.bottom + 5)
        surface.blit(label, label_rect)

    def _draw_chart(self, surface: pygame.Surface) -> None:
        chart_top = self.READOUT_HEIGHT + 10
        chart_left = self.CHART_LEFT
        chart_right = SCREEN_WIDTH - self.CHART_RIGHT
        chart_bottom = SCREEN_HEIGHT - self.CHART_BOTTOM
        chart_width = chart_right - chart_left
        chart_height = chart_bottom - chart_top

        # Chart background
        pygame.draw.rect(
            surface, COLOR_CHART_BG, (chart_left, chart_top, chart_width, chart_height)
        )

        # Grid lines and labels
        db_range = SPL_MAX - SPL_MIN
        grid_step = 10
        for db in range(int(SPL_MIN), int(SPL_MAX) + 1, grid_step):
            y = chart_bottom - (db - SPL_MIN) / db_range * chart_height
            pygame.draw.line(surface, COLOR_GRID, (chart_left, int(y)), (chart_right, int(y)))
            label = self._font_small.render(f"{db}", True, COLOR_TEXT)
            lx = chart_left - label.get_width() - 8
            ly = int(y) - label.get_height() // 2
            surface.blit(label, (lx, ly))

        # Time labels
        time_step = 5 if self.settings.history_seconds <= 60 else 30
        for sec in range(0, self.settings.history_seconds + 1, time_step):
            x = chart_left + sec / self.settings.history_seconds * chart_width
            pygame.draw.line(surface, COLOR_GRID, (int(x), chart_top), (int(x), chart_bottom))
            time_label = f"-{self.settings.history_seconds - sec}s"
            label = self._font_small.render(time_label, True, COLOR_TEXT)
            surface.blit(label, (int(x) - label.get_width() // 2, chart_bottom + 5))

        # Plot history
        if len(self._history) < 2:
            return

        points = []
        n = len(self._history)
        for i, db in enumerate(self._history):
            # Align to right edge — most recent sample at chart_right
            x = chart_right - (n - 1 - i) / max(self.settings.history_length - 1, 1) * chart_width
            clamped = max(SPL_MIN, min(SPL_MAX, db))
            y = chart_bottom - (clamped - SPL_MIN) / db_range * chart_height
            points.append((x, y))

        # Draw line segments colored by level
        for i in range(1, len(points)):
            db_val = self._history[i]
            color = self._spl_color(db_val)
            pygame.draw.line(surface, color, points[i - 1], points[i], 2)

        # Chart border
        pygame.draw.rect(surface, COLOR_GRID, (chart_left, chart_top, chart_width, chart_height), 1)

    def _draw_buttons(self, surface: pygame.Surface) -> None:
        # Position buttons in top-right corner
        x = SCREEN_WIDTH - self.BUTTON_WIDTH - self.BUTTON_MARGIN
        y = self.BUTTON_MARGIN

        # EXIT button
        self._exit_button_rect = pygame.Rect(x, y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
        self._draw_text_button(
            surface, self._exit_button_rect, "EXIT", self._hovered_button == "exit"
        )

        # SETTINGS button (below EXIT) - with gear icon
        y += self.BUTTON_HEIGHT + self.BUTTON_SPACING
        self._settings_button_rect = pygame.Rect(x, y, self.BUTTON_WIDTH, self.BUTTON_HEIGHT)
        self._draw_icon_button(
            surface, self._settings_button_rect, self._hovered_button == "settings"
        )

    def _draw_text_button(
        self, surface: pygame.Surface, rect: pygame.Rect, text: str, is_hovered: bool
    ) -> None:
        # Choose color based on hover state
        bg_color = COLOR_BUTTON_HOVER if is_hovered else COLOR_BUTTON_BG

        # Draw button background
        pygame.draw.rect(surface, bg_color, rect)
        pygame.draw.rect(surface, COLOR_BUTTON_TEXT, rect, 2)

        # Draw button text
        button_text = self._font_medium.render(text, True, COLOR_BUTTON_TEXT)
        text_rect = button_text.get_rect(center=rect.center)
        surface.blit(button_text, text_rect)

    def _draw_icon_button(
        self, surface: pygame.Surface, rect: pygame.Rect, is_hovered: bool
    ) -> None:
        # Choose color based on hover state
        bg_color = COLOR_BUTTON_HOVER if is_hovered else COLOR_BUTTON_BG

        # Draw button background
        pygame.draw.rect(surface, bg_color, rect)
        pygame.draw.rect(surface, COLOR_BUTTON_TEXT, rect, 2)

        # Draw gear icon using Unicode ⚙ character
        icon = self._font_icon.render("\u2699", True, COLOR_BUTTON_TEXT)
        icon_rect = icon.get_rect(center=rect.center)
        surface.blit(icon, icon_rect)
