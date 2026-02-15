import pygame

from pi_audio.config import (
    COLOR_BG,
    COLOR_BUTTON_BG,
    COLOR_BUTTON_HOVER,
    COLOR_BUTTON_TEXT,
    COLOR_DIVIDER,
    COLOR_LABEL_DIM,
    COLOR_SLIDER_FILL,
    COLOR_SLIDER_HANDLE,
    COLOR_SLIDER_HANDLE_ACTIVE,
    COLOR_SLIDER_TRACK,
    COLOR_TEXT,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
)
from pi_audio.screens.base import Screen
from pi_audio.settings import Settings


class _SliderDef:
    """Definition for a single slider control."""

    def __init__(
        self,
        key: str,
        label: str,
        unit: str,
        min_val: float,
        max_val: float,
        step: float,
        fmt: str = ".0f",
    ):
        self.key = key
        self.label = label
        self.unit = unit
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.fmt = fmt


SLIDERS = [
    _SliderDef("history_seconds", "History Length", "s", 5, 300, 5),
    _SliderDef("quiet_threshold", "Safe Threshold", "dB", 20, 95, 1),
    _SliderDef("moderate_threshold", "Caution Threshold", "dB", 21, 100, 1),
]


class SettingsScreen(Screen):
    # Layout
    SLIDER_WIDTH = 500
    SLIDER_HEIGHT = 8
    HANDLE_RADIUS = 14
    ROW_HEIGHT = 100
    CONTENT_TOP = 110
    BACK_BUTTON_WIDTH = 140
    BACK_BUTTON_HEIGHT = 48

    def __init__(self, settings: Settings, on_back: callable):
        self.settings = settings
        self.on_back = on_back
        self._font_title: pygame.font.Font | None = None
        self._font_label: pygame.font.Font | None = None
        self._font_value: pygame.font.Font | None = None
        self._font_hint: pygame.font.Font | None = None
        self._dragging: str | None = None
        self._hovered_slider: str | None = None
        self._back_hovered: bool = False
        self._back_rect: pygame.Rect | None = None
        self._slider_rects: dict[str, pygame.Rect] = {}

    def _ensure_fonts(self) -> None:
        if self._font_title is None:
            self._font_title = pygame.font.SysFont("monospace", 40, bold=True)
            self._font_label = pygame.font.SysFont("monospace", 24)
            self._font_value = pygame.font.SysFont("monospace", 24, bold=True)
            self._font_hint = pygame.font.SysFont("monospace", 16)

    def _slider_x_start(self) -> int:
        return (SCREEN_WIDTH - self.SLIDER_WIDTH) // 2

    def _get_value(self, slider: _SliderDef) -> float:
        return float(getattr(self.settings, slider.key))

    def _set_value(self, slider: _SliderDef, val: float) -> None:
        snapped = round(val / slider.step) * slider.step
        clamped = max(slider.min_val, min(slider.max_val, snapped))
        if isinstance(getattr(self.settings, slider.key), int):
            setattr(self.settings, slider.key, int(clamped))
        else:
            setattr(self.settings, slider.key, clamped)
        self.settings.validate_and_clamp()

    def _fraction(self, slider: _SliderDef) -> float:
        val = self._get_value(slider)
        if slider.max_val == slider.min_val:
            return 0.0
        return (val - slider.min_val) / (slider.max_val - slider.min_val)

    def _value_from_x(self, slider: _SliderDef, x: int) -> float:
        sx = self._slider_x_start()
        frac = max(0.0, min(1.0, (x - sx) / self.SLIDER_WIDTH))
        return slider.min_val + frac * (slider.max_val - slider.min_val)

    def _row_y(self, index: int) -> int:
        return self.CONTENT_TOP + index * self.ROW_HEIGHT

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            # Update hover states
            self._back_hovered = bool(self._back_rect and self._back_rect.collidepoint(mx, my))
            self._hovered_slider = None
            for i, slider in enumerate(SLIDERS):
                rect = self._slider_rects.get(slider.key)
                if rect and rect.collidepoint(mx, my):
                    self._hovered_slider = slider.key

            # Handle drag
            if self._dragging:
                for slider in SLIDERS:
                    if slider.key == self._dragging:
                        self._set_value(slider, self._value_from_x(slider, mx))
                        break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self._back_rect and self._back_rect.collidepoint(mx, my):
                self.on_back()
                return

            # Check slider hit areas
            for i, slider in enumerate(SLIDERS):
                rect = self._slider_rects.get(slider.key)
                if rect and rect.collidepoint(mx, my):
                    self._dragging = slider.key
                    self._set_value(slider, self._value_from_x(slider, mx))
                    break

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = None

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        surface.fill(COLOR_BG)
        self._slider_rects.clear()

        # Title
        title = self._font_title.render("Settings", True, COLOR_TEXT)
        title_rect = title.get_rect(centerx=SCREEN_WIDTH // 2, top=30)
        surface.blit(title, title_rect)

        # Divider under title
        div_y = title_rect.bottom + 16
        pygame.draw.line(surface, COLOR_DIVIDER, (80, div_y), (SCREEN_WIDTH - 80, div_y))

        # Slider rows
        for i, slider in enumerate(SLIDERS):
            self._draw_slider_row(surface, i, slider)

        # Back button
        bx = (SCREEN_WIDTH - self.BACK_BUTTON_WIDTH) // 2
        by = SCREEN_HEIGHT - 80
        self._back_rect = pygame.Rect(bx, by, self.BACK_BUTTON_WIDTH, self.BACK_BUTTON_HEIGHT)
        bg = COLOR_BUTTON_HOVER if self._back_hovered else COLOR_BUTTON_BG
        pygame.draw.rect(surface, bg, self._back_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_BUTTON_TEXT, self._back_rect, 2, border_radius=6)
        btn_text = self._font_label.render("Back", True, COLOR_BUTTON_TEXT)
        surface.blit(btn_text, btn_text.get_rect(center=self._back_rect.center))

    def _draw_slider_row(self, surface: pygame.Surface, index: int, slider: _SliderDef) -> None:
        y = self._row_y(index)
        sx = self._slider_x_start()
        frac = self._fraction(slider)
        val = self._get_value(slider)
        is_active = self._dragging == slider.key
        is_hovered = self._hovered_slider == slider.key

        # Label (left-aligned above slider)
        label = self._font_label.render(slider.label, True, COLOR_TEXT)
        surface.blit(label, (sx, y))

        # Value (right-aligned above slider)
        val_str = f"{val:{slider.fmt}}{slider.unit}"
        val_surf = self._font_value.render(val_str, True, COLOR_SLIDER_FILL)
        surface.blit(val_surf, (sx + self.SLIDER_WIDTH - val_surf.get_width(), y))

        # Range hints
        lo = self._font_hint.render(f"{slider.min_val:{slider.fmt}}", True, COLOR_LABEL_DIM)
        hi = self._font_hint.render(f"{slider.max_val:{slider.fmt}}", True, COLOR_LABEL_DIM)

        track_y = y + 40
        # Track background
        track_rect = pygame.Rect(sx, track_y, self.SLIDER_WIDTH, self.SLIDER_HEIGHT)
        pygame.draw.rect(surface, COLOR_SLIDER_TRACK, track_rect, border_radius=4)

        # Filled portion
        fill_w = int(frac * self.SLIDER_WIDTH)
        if fill_w > 0:
            fill_rect = pygame.Rect(sx, track_y, fill_w, self.SLIDER_HEIGHT)
            pygame.draw.rect(surface, COLOR_SLIDER_FILL, fill_rect, border_radius=4)

        # Handle
        handle_x = sx + int(frac * self.SLIDER_WIDTH)
        handle_y = track_y + self.SLIDER_HEIGHT // 2
        radius = self.HANDLE_RADIUS + (2 if is_active else (1 if is_hovered else 0))
        handle_color = COLOR_SLIDER_HANDLE_ACTIVE if is_active else COLOR_SLIDER_HANDLE
        pygame.draw.circle(surface, handle_color, (handle_x, handle_y), radius)

        # Hit area for mouse interaction (generous vertical area)
        hit_rect = pygame.Rect(
            sx - self.HANDLE_RADIUS,
            track_y - 20,
            self.SLIDER_WIDTH + self.HANDLE_RADIUS * 2,
            self.SLIDER_HEIGHT + 40,
        )
        self._slider_rects[slider.key] = hit_rect

        # Range labels below track
        surface.blit(lo, (sx, track_y + self.SLIDER_HEIGHT + 6))
        hi_x = sx + self.SLIDER_WIDTH - hi.get_width()
        surface.blit(hi, (hi_x, track_y + self.SLIDER_HEIGHT + 6))

        # Divider below row (except last)
        if index < len(SLIDERS) - 1:
            div_y = track_y + self.SLIDER_HEIGHT + 32
            pygame.draw.line(surface, COLOR_DIVIDER, (sx, div_y), (sx + self.SLIDER_WIDTH, div_y))
