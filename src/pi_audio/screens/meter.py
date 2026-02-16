import numpy as np
import pygame

from pi_audio.config import (
    BLOCK_SIZE,
    COLOR_BG,
    COLOR_BUTTON_HOVER,
    COLOR_CHART_BG,
    COLOR_GREEN,
    COLOR_GRID,
    COLOR_RED,
    COLOR_TEXT,
    COLOR_YELLOW,
    SAMPLE_RATE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SPL_MAX,
    SPL_MIN,
)
from pi_audio.screens.base import Screen
from pi_audio.settings import Settings
from pi_audio.spectrogram import SpectrogramRenderer


class MeterScreen(Screen):
    # Layout
    READOUT_HEIGHT = 90
    CHART_LEFT_SPL = 80  # left margin when SPL y-axis labels are needed
    CHART_LEFT_SPEC = 50  # left margin for spectrogram freq labels
    CHART_RIGHT = 20
    CHART_BOTTOM = 40
    CHART_BOTTOM_SPEC = 10  # less bottom margin when no time labels

    # Hamburger menu dimensions
    MENU_ICON_SIZE = 40
    MENU_ICON_MARGIN = 10
    MENU_DROPDOWN_WIDTH = 160
    MENU_ITEM_HEIGHT = 44

    def __init__(self, settings: Settings, on_settings: callable):
        self.settings = settings
        self.on_settings = on_settings
        self._spl: float = 0.0
        self._history: list[float] = []
        self._spectrogram: list[np.ndarray] = []
        self._spec_renderer = SpectrogramRenderer(SAMPLE_RATE, BLOCK_SIZE)
        self._font_large: pygame.font.Font | None = None
        self._font_medium: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None
        self._font_icon: pygame.font.Font | None = None
        self._menu_icon_rect: pygame.Rect | None = None
        self._menu_open: bool = False
        self._menu_settings_rect: pygame.Rect | None = None
        self._menu_exit_rect: pygame.Rect | None = None
        self._hovered_menu_item: str | None = None

    def _ensure_fonts(self) -> None:
        if self._font_large is None:
            self._font_large = pygame.font.SysFont("monospace", 120, bold=True)
            self._font_medium = pygame.font.SysFont("monospace", 28)
            self._font_small = pygame.font.SysFont("monospace", 18)
            self._font_icon = pygame.font.SysFont("monospace", 20)

    def set_audio_data(
        self,
        spl: float,
        history: list[float],
        spectrogram: list[np.ndarray] | None = None,
    ) -> None:
        self._spl = spl
        self._history = history
        if spectrogram is not None:
            self._spectrogram = spectrogram

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hovered_menu_item = None
            if self._menu_open:
                if self._menu_settings_rect and self._menu_settings_rect.collidepoint(event.pos):
                    self._hovered_menu_item = "settings"
                elif self._menu_exit_rect and self._menu_exit_rect.collidepoint(event.pos):
                    self._hovered_menu_item = "exit"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._menu_open:
                if self._menu_settings_rect and self._menu_settings_rect.collidepoint(event.pos):
                    self._menu_open = False
                    self.on_settings()
                elif self._menu_exit_rect and self._menu_exit_rect.collidepoint(event.pos):
                    raise SystemExit
                else:
                    self._menu_open = False
            elif self._menu_icon_rect and self._menu_icon_rect.collidepoint(event.pos):
                self._menu_open = True

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        surface.fill(COLOR_BG)
        self._draw_readout(surface)
        self._draw_chart(surface)
        self._draw_menu(surface)

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

        # Main number — positioned near the top
        text = f"{self._spl:5.1f}"
        rendered = self._font_large.render(text, True, color)
        rect = rendered.get_rect(centerx=SCREEN_WIDTH // 2, centery=self.READOUT_HEIGHT // 2)
        surface.blit(rendered, rect)

    def _draw_chart(self, surface: pygame.Surface) -> None:
        chart_top = self.READOUT_HEIGHT + 5
        mode = self.settings.display_mode

        if mode == "meter":
            chart_left = self.CHART_LEFT_SPL
            chart_right = SCREEN_WIDTH - self.CHART_RIGHT
            chart_bottom = SCREEN_HEIGHT - self.CHART_BOTTOM
            chart_width = chart_right - chart_left
            chart_height = chart_bottom - chart_top
            self._draw_spl_chart(surface, chart_left, chart_top, chart_width, chart_height)
        elif mode == "overtones":
            chart_left = self.CHART_LEFT_SPEC
            chart_right = SCREEN_WIDTH - self.CHART_RIGHT
            chart_bottom = SCREEN_HEIGHT - self.CHART_BOTTOM_SPEC
            chart_width = chart_right - chart_left
            chart_height = chart_bottom - chart_top
            self._draw_spectrogram(surface, chart_left, chart_top, chart_width, chart_height)
        else:  # "both"
            chart_bottom_spec = SCREEN_HEIGHT - self.CHART_BOTTOM_SPEC
            chart_bottom_spl = SCREEN_HEIGHT - self.CHART_BOTTOM
            gap = 60  # room for SPL y-axis labels between the two charts
            total_width = SCREEN_WIDTH - self.CHART_LEFT_SPEC - self.CHART_RIGHT
            half = (total_width - gap) // 2
            spec_left = self.CHART_LEFT_SPEC
            spec_height = chart_bottom_spec - chart_top
            self._draw_spectrogram(surface, spec_left, chart_top, half, spec_height)
            spl_left = spec_left + half + gap
            spl_height = chart_bottom_spl - chart_top
            self._draw_spl_chart(surface, spl_left, chart_top, total_width - half - gap, spl_height)

    def _draw_spectrogram(
        self, surface: pygame.Surface, left: int, top: int, width: int, height: int
    ) -> None:
        # Background
        pygame.draw.rect(surface, COLOR_CHART_BG, (left, top, width, height))
        rect = pygame.Rect(left, top, width, height)
        self._spec_renderer.draw(surface, rect, self._spectrogram)
        # Border
        pygame.draw.rect(surface, COLOR_GRID, (left, top, width, height), 1)

    def _draw_spl_chart(
        self, surface: pygame.Surface, left: int, top: int, width: int, height: int
    ) -> None:
        right = left + width
        bottom = top + height

        # Chart background
        pygame.draw.rect(surface, COLOR_CHART_BG, (left, top, width, height))

        # Grid lines and labels
        db_range = SPL_MAX - SPL_MIN
        grid_step = 10
        for db in range(int(SPL_MIN), int(SPL_MAX) + 1, grid_step):
            y = bottom - (db - SPL_MIN) / db_range * height
            pygame.draw.line(surface, COLOR_GRID, (left, int(y)), (right, int(y)))
            label = self._font_small.render(f"{db}", True, COLOR_TEXT)
            lx = left - label.get_width() - 8
            ly = int(y) - label.get_height() // 2
            surface.blit(label, (lx, ly))

        # Time labels
        time_step = 5 if self.settings.history_seconds <= 60 else 30
        for sec in range(0, self.settings.history_seconds + 1, time_step):
            x = left + sec / self.settings.history_seconds * width
            pygame.draw.line(surface, COLOR_GRID, (int(x), top), (int(x), bottom))
            time_label = f"-{self.settings.history_seconds - sec}s"
            label = self._font_small.render(time_label, True, COLOR_TEXT)
            surface.blit(label, (int(x) - label.get_width() // 2, bottom + 5))

        # Plot history
        if len(self._history) < 2:
            pygame.draw.rect(surface, COLOR_GRID, (left, top, width, height), 1)
            return

        points = []
        n = len(self._history)
        for i, db in enumerate(self._history):
            x = right - (n - 1 - i) / max(self.settings.history_length - 1, 1) * width
            clamped = max(SPL_MIN, min(SPL_MAX, db))
            y = bottom - (clamped - SPL_MIN) / db_range * height
            points.append((x, y))

        # Draw line segments colored by level
        for i in range(1, len(points)):
            db_val = self._history[i]
            color = self._spl_color(db_val)
            pygame.draw.line(surface, color, points[i - 1], points[i], 2)

        # Chart border
        pygame.draw.rect(surface, COLOR_GRID, (left, top, width, height), 1)

    def _draw_menu(self, surface: pygame.Surface) -> None:
        # Hamburger icon in upper-right corner
        ix = SCREEN_WIDTH - self.MENU_ICON_SIZE - self.MENU_ICON_MARGIN
        iy = self.MENU_ICON_MARGIN
        self._menu_icon_rect = pygame.Rect(ix, iy, self.MENU_ICON_SIZE, self.MENU_ICON_SIZE)

        # Draw three horizontal lines (hamburger)
        line_color = COLOR_TEXT
        line_width = 22
        line_thickness = 3
        cx = ix + self.MENU_ICON_SIZE // 2
        cy = iy + self.MENU_ICON_SIZE // 2
        for offset in (-8, 0, 8):
            x0 = cx - line_width // 2
            x1 = cx + line_width // 2
            y = cy + offset
            pygame.draw.line(surface, line_color, (x0, y), (x1, y), line_thickness)

        # Draw dropdown if open
        if self._menu_open:
            dx = SCREEN_WIDTH - self.MENU_DROPDOWN_WIDTH - self.MENU_ICON_MARGIN
            dy = iy + self.MENU_ICON_SIZE + 4

            # Dropdown background
            dropdown_rect = pygame.Rect(dx, dy, self.MENU_DROPDOWN_WIDTH, self.MENU_ITEM_HEIGHT * 2)
            pygame.draw.rect(surface, (50, 50, 65), dropdown_rect)
            pygame.draw.rect(surface, (80, 80, 100), dropdown_rect, 1)

            # Settings item
            self._menu_settings_rect = pygame.Rect(
                dx, dy, self.MENU_DROPDOWN_WIDTH, self.MENU_ITEM_HEIGHT
            )
            if self._hovered_menu_item == "settings":
                pygame.draw.rect(surface, COLOR_BUTTON_HOVER, self._menu_settings_rect)
            settings_text = self._font_icon.render("Settings", True, COLOR_TEXT)
            surface.blit(
                settings_text,
                settings_text.get_rect(midleft=(dx + 12, dy + self.MENU_ITEM_HEIGHT // 2)),
            )

            # Divider
            pygame.draw.line(
                surface,
                (80, 80, 100),
                (dx + 8, dy + self.MENU_ITEM_HEIGHT),
                (dx + self.MENU_DROPDOWN_WIDTH - 8, dy + self.MENU_ITEM_HEIGHT),
            )

            # Exit item
            ey = dy + self.MENU_ITEM_HEIGHT
            self._menu_exit_rect = pygame.Rect(
                dx, ey, self.MENU_DROPDOWN_WIDTH, self.MENU_ITEM_HEIGHT
            )
            if self._hovered_menu_item == "exit":
                pygame.draw.rect(surface, COLOR_BUTTON_HOVER, self._menu_exit_rect)
            exit_text = self._font_icon.render("Exit", True, COLOR_TEXT)
            surface.blit(
                exit_text,
                exit_text.get_rect(midleft=(dx + 12, ey + self.MENU_ITEM_HEIGHT // 2)),
            )
