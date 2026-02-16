import math

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
    """Definition for a single-handle slider control."""

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


# Groups: (heading, list of slider defs)
_GENERAL_SLIDERS = [
    _SliderDef("history_seconds", "History Length", "s", 5, 300, 5),
]
_LEVEL_SLIDERS = [
    _SliderDef("quiet_threshold", "Safe Threshold", "dB", 20, 95, 1),
    _SliderDef("moderate_threshold", "Caution Threshold", "dB", 21, 100, 1),
]

# Overtone range slider constants (logarithmic)
_RANGE_FREQ_MIN = 40.0
_RANGE_FREQ_MAX = 8000.0
_RANGE_LOG_MIN = math.log10(_RANGE_FREQ_MIN)
_RANGE_LOG_MAX = math.log10(_RANGE_FREQ_MAX)
_RANGE_STEP = 10  # Hz


def _freq_to_frac(freq: float) -> float:
    """Map a frequency to 0..1 on a logarithmic scale."""
    return (math.log10(max(freq, _RANGE_FREQ_MIN)) - _RANGE_LOG_MIN) / (
        _RANGE_LOG_MAX - _RANGE_LOG_MIN
    )


def _frac_to_freq(frac: float) -> float:
    """Map 0..1 back to a frequency on a logarithmic scale."""
    frac = max(0.0, min(1.0, frac))
    return 10.0 ** (_RANGE_LOG_MIN + frac * (_RANGE_LOG_MAX - _RANGE_LOG_MIN))


def _fmt_freq(hz: float) -> str:
    """Format a frequency value for display."""
    if hz >= 1000:
        khz = hz / 1000
        if khz == int(khz):
            return f"{int(khz)}k Hz"
        return f"{khz:.1f}k Hz"
    return f"{int(hz)} Hz"


class SettingsScreen(Screen):
    # Layout constants
    CONTENT_WIDTH = 500
    SLIDER_HEIGHT = 8
    HANDLE_RADIUS = 12
    SLIDER_ROW_HEIGHT = 58
    GROUP_HEADING_HEIGHT = 28
    GROUP_GAP = 14
    BACK_BUTTON_WIDTH = 140
    BACK_BUTTON_HEIGHT = 44

    def __init__(self, settings: Settings, on_back: callable):
        self.settings = settings
        self.on_back = on_back
        self._font_title: pygame.font.Font | None = None
        self._font_group: pygame.font.Font | None = None
        self._font_label: pygame.font.Font | None = None
        self._font_value: pygame.font.Font | None = None
        self._font_hint: pygame.font.Font | None = None
        self._dragging: str | None = None  # slider key or "range_min"/"range_max"
        self._hovered_slider: str | None = None
        self._back_hovered: bool = False
        self._back_rect: pygame.Rect | None = None
        self._slider_rects: dict[str, pygame.Rect] = {}
        self._range_hit_rect: pygame.Rect | None = None

    def _ensure_fonts(self) -> None:
        if self._font_title is None:
            self._font_title = pygame.font.SysFont("monospace", 36, bold=True)
            self._font_group = pygame.font.SysFont("monospace", 18, bold=True)
            self._font_label = pygame.font.SysFont("monospace", 20)
            self._font_value = pygame.font.SysFont("monospace", 20, bold=True)
            self._font_hint = pygame.font.SysFont("monospace", 14)

    @property
    def _content_left(self) -> int:
        return (SCREEN_WIDTH - self.CONTENT_WIDTH) // 2

    # --- Single slider helpers ---

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
        self.settings.save()

    def _fraction(self, slider: _SliderDef) -> float:
        val = self._get_value(slider)
        if slider.max_val == slider.min_val:
            return 0.0
        return (val - slider.min_val) / (slider.max_val - slider.min_val)

    def _value_from_x(self, slider: _SliderDef, x: int) -> float:
        sx = self._content_left
        frac = max(0.0, min(1.0, (x - sx) / self.CONTENT_WIDTH))
        return slider.min_val + frac * (slider.max_val - slider.min_val)

    # --- Range slider helpers ---

    def _range_value_from_x(self, x: int) -> float:
        sx = self._content_left
        frac = max(0.0, min(1.0, (x - sx) / self.CONTENT_WIDTH))
        raw = _frac_to_freq(frac)
        return round(raw / _RANGE_STEP) * _RANGE_STEP

    def _set_range_value(self, handle: str, freq: float) -> None:
        freq = max(_RANGE_FREQ_MIN, min(_RANGE_FREQ_MAX, freq))
        freq = int(round(freq / _RANGE_STEP) * _RANGE_STEP)
        if handle == "range_min":
            self.settings.overtone_freq_min = freq
        else:
            self.settings.overtone_freq_max = freq
        self.settings.validate_and_clamp()
        self.settings.save()

    # --- Event handling ---

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self._back_hovered = bool(self._back_rect and self._back_rect.collidepoint(mx, my))

            self._hovered_slider = None
            for key, rect in self._slider_rects.items():
                if rect.collidepoint(mx, my):
                    self._hovered_slider = key
            if self._range_hit_rect and self._range_hit_rect.collidepoint(mx, my):
                # Determine which handle is closer
                min_frac = _freq_to_frac(self.settings.overtone_freq_min)
                max_frac = _freq_to_frac(self.settings.overtone_freq_max)
                sx = self._content_left
                min_x = sx + min_frac * self.CONTENT_WIDTH
                max_x = sx + max_frac * self.CONTENT_WIDTH
                if abs(mx - min_x) <= abs(mx - max_x):
                    self._hovered_slider = "range_min"
                else:
                    self._hovered_slider = "range_max"

            # Handle drag
            if self._dragging:
                if self._dragging in ("range_min", "range_max"):
                    self._set_range_value(self._dragging, self._range_value_from_x(mx))
                else:
                    all_sliders = _GENERAL_SLIDERS + _LEVEL_SLIDERS
                    for slider in all_sliders:
                        if slider.key == self._dragging:
                            self._set_value(slider, self._value_from_x(slider, mx))
                            break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self._back_rect and self._back_rect.collidepoint(mx, my):
                self.on_back()
                return

            # Check range slider
            if self._range_hit_rect and self._range_hit_rect.collidepoint(mx, my):
                min_frac = _freq_to_frac(self.settings.overtone_freq_min)
                max_frac = _freq_to_frac(self.settings.overtone_freq_max)
                sx = self._content_left
                min_x = sx + min_frac * self.CONTENT_WIDTH
                max_x = sx + max_frac * self.CONTENT_WIDTH
                if abs(mx - min_x) <= abs(mx - max_x):
                    self._dragging = "range_min"
                else:
                    self._dragging = "range_max"
                self._set_range_value(self._dragging, self._range_value_from_x(mx))
                return

            # Check single sliders
            for key, rect in self._slider_rects.items():
                if rect.collidepoint(mx, my):
                    self._dragging = key
                    all_sliders = _GENERAL_SLIDERS + _LEVEL_SLIDERS
                    for slider in all_sliders:
                        if slider.key == key:
                            self._set_value(slider, self._value_from_x(slider, mx))
                            break
                    break

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = None

    def update(self, dt: float) -> None:
        pass

    # --- Drawing ---

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        surface.fill(COLOR_BG)
        self._slider_rects.clear()

        sx = self._content_left
        y = 20

        # Title
        title = self._font_title.render("Settings", True, COLOR_TEXT)
        title_rect = title.get_rect(centerx=SCREEN_WIDTH // 2, top=y)
        surface.blit(title, title_rect)
        y = title_rect.bottom + 10
        pygame.draw.line(surface, COLOR_DIVIDER, (sx, y), (sx + self.CONTENT_WIDTH, y))
        y += self.GROUP_GAP

        # Group 1: General (history + display mode)
        y = self._draw_group_heading(surface, "General", y)
        for slider in _GENERAL_SLIDERS:
            y = self._draw_slider(surface, slider, y)
        y += self.GROUP_GAP
        pygame.draw.line(surface, COLOR_DIVIDER, (sx, y), (sx + self.CONTENT_WIDTH, y))
        y += self.GROUP_GAP

        # Group 2: Sound Levels
        y = self._draw_group_heading(surface, "Sound Levels", y)
        for slider in _LEVEL_SLIDERS:
            y = self._draw_slider(surface, slider, y)
        y += self.GROUP_GAP
        pygame.draw.line(surface, COLOR_DIVIDER, (sx, y), (sx + self.CONTENT_WIDTH, y))
        y += self.GROUP_GAP

        # Group 3: Overtones (range slider)
        y = self._draw_group_heading(surface, "Overtones", y)
        y = self._draw_range_slider(surface, y)

        # Back button
        bx = (SCREEN_WIDTH - self.BACK_BUTTON_WIDTH) // 2
        by = SCREEN_HEIGHT - 64
        self._back_rect = pygame.Rect(bx, by, self.BACK_BUTTON_WIDTH, self.BACK_BUTTON_HEIGHT)
        bg = COLOR_BUTTON_HOVER if self._back_hovered else COLOR_BUTTON_BG
        pygame.draw.rect(surface, bg, self._back_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_BUTTON_TEXT, self._back_rect, 2, border_radius=6)
        btn_text = self._font_label.render("Back", True, COLOR_BUTTON_TEXT)
        surface.blit(btn_text, btn_text.get_rect(center=self._back_rect.center))

    def _draw_group_heading(self, surface: pygame.Surface, text: str, y: int) -> int:
        sx = self._content_left
        label = self._font_group.render(text, True, COLOR_LABEL_DIM)
        surface.blit(label, (sx, y))
        return y + self.GROUP_HEADING_HEIGHT

    def _draw_slider(self, surface: pygame.Surface, slider: _SliderDef, y: int) -> int:
        sx = self._content_left
        frac = self._fraction(slider)
        val = self._get_value(slider)
        is_active = self._dragging == slider.key
        is_hovered = self._hovered_slider == slider.key

        # Label + value on same line
        label = self._font_label.render(slider.label, True, COLOR_TEXT)
        surface.blit(label, (sx, y))
        val_str = f"{val:{slider.fmt}}{slider.unit}"
        val_surf = self._font_value.render(val_str, True, COLOR_SLIDER_FILL)
        surface.blit(val_surf, (sx + self.CONTENT_WIDTH - val_surf.get_width(), y))

        track_y = y + 28
        track_rect = pygame.Rect(sx, track_y, self.CONTENT_WIDTH, self.SLIDER_HEIGHT)
        pygame.draw.rect(surface, COLOR_SLIDER_TRACK, track_rect, border_radius=4)

        fill_w = int(frac * self.CONTENT_WIDTH)
        if fill_w > 0:
            fill_rect = pygame.Rect(sx, track_y, fill_w, self.SLIDER_HEIGHT)
            pygame.draw.rect(surface, COLOR_SLIDER_FILL, fill_rect, border_radius=4)

        handle_x = sx + int(frac * self.CONTENT_WIDTH)
        handle_y = track_y + self.SLIDER_HEIGHT // 2
        radius = self.HANDLE_RADIUS + (2 if is_active else (1 if is_hovered else 0))
        handle_color = COLOR_SLIDER_HANDLE_ACTIVE if is_active else COLOR_SLIDER_HANDLE
        pygame.draw.circle(surface, handle_color, (handle_x, handle_y), radius)

        hit_rect = pygame.Rect(
            sx - self.HANDLE_RADIUS,
            track_y - 16,
            self.CONTENT_WIDTH + self.HANDLE_RADIUS * 2,
            self.SLIDER_HEIGHT + 32,
        )
        self._slider_rects[slider.key] = hit_rect

        # Range hints
        lo = self._font_hint.render(f"{slider.min_val:{slider.fmt}}", True, COLOR_LABEL_DIM)
        hi = self._font_hint.render(f"{slider.max_val:{slider.fmt}}", True, COLOR_LABEL_DIM)
        hint_y = track_y + self.SLIDER_HEIGHT + 4
        surface.blit(lo, (sx, hint_y))
        surface.blit(hi, (sx + self.CONTENT_WIDTH - hi.get_width(), hint_y))

        return y + self.SLIDER_ROW_HEIGHT

    def _draw_range_slider(self, surface: pygame.Surface, y: int) -> int:
        sx = self._content_left
        freq_min = self.settings.overtone_freq_min
        freq_max = self.settings.overtone_freq_max
        frac_min = _freq_to_frac(freq_min)
        frac_max = _freq_to_frac(freq_max)

        is_min_active = self._dragging == "range_min"
        is_max_active = self._dragging == "range_max"
        is_min_hovered = self._hovered_slider == "range_min"
        is_max_hovered = self._hovered_slider == "range_max"

        # Label + current range value
        label = self._font_label.render("Frequency Range", True, COLOR_TEXT)
        surface.blit(label, (sx, y))
        range_str = f"{_fmt_freq(freq_min)} \u2013 {_fmt_freq(freq_max)}"
        val_surf = self._font_value.render(range_str, True, COLOR_SLIDER_FILL)
        surface.blit(val_surf, (sx + self.CONTENT_WIDTH - val_surf.get_width(), y))

        track_y = y + 28

        # Full track background
        track_rect = pygame.Rect(sx, track_y, self.CONTENT_WIDTH, self.SLIDER_HEIGHT)
        pygame.draw.rect(surface, COLOR_SLIDER_TRACK, track_rect, border_radius=4)

        # Filled portion between the two handles
        fill_x = sx + int(frac_min * self.CONTENT_WIDTH)
        fill_w = int((frac_max - frac_min) * self.CONTENT_WIDTH)
        if fill_w > 0:
            fill_rect = pygame.Rect(fill_x, track_y, fill_w, self.SLIDER_HEIGHT)
            pygame.draw.rect(surface, COLOR_SLIDER_FILL, fill_rect, border_radius=4)

        handle_cy = track_y + self.SLIDER_HEIGHT // 2

        # Min handle
        min_hx = sx + int(frac_min * self.CONTENT_WIDTH)
        r_min = self.HANDLE_RADIUS + (2 if is_min_active else (1 if is_min_hovered else 0))
        c_min = COLOR_SLIDER_HANDLE_ACTIVE if is_min_active else COLOR_SLIDER_HANDLE
        pygame.draw.circle(surface, c_min, (min_hx, handle_cy), r_min)

        # Max handle
        max_hx = sx + int(frac_max * self.CONTENT_WIDTH)
        r_max = self.HANDLE_RADIUS + (2 if is_max_active else (1 if is_max_hovered else 0))
        c_max = COLOR_SLIDER_HANDLE_ACTIVE if is_max_active else COLOR_SLIDER_HANDLE
        pygame.draw.circle(surface, c_max, (max_hx, handle_cy), r_max)

        # Hit area
        self._range_hit_rect = pygame.Rect(
            sx - self.HANDLE_RADIUS,
            track_y - 16,
            self.CONTENT_WIDTH + self.HANDLE_RADIUS * 2,
            self.SLIDER_HEIGHT + 32,
        )

        # Range hints
        lo = self._font_hint.render(_fmt_freq(_RANGE_FREQ_MIN), True, COLOR_LABEL_DIM)
        hi = self._font_hint.render(_fmt_freq(_RANGE_FREQ_MAX), True, COLOR_LABEL_DIM)
        hint_y = track_y + self.SLIDER_HEIGHT + 4
        surface.blit(lo, (sx, hint_y))
        surface.blit(hi, (sx + self.CONTENT_WIDTH - hi.get_width(), hint_y))

        return y + self.SLIDER_ROW_HEIGHT
