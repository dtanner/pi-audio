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
from pi_audio.pitch import note_name_from_semitone
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
    _SliderDef("quiet_threshold", "Safe Threshold", "dB", 40, 95, 1),
    _SliderDef("moderate_threshold", "Caution Threshold", "dB", 60, 100, 1),
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


# Pitch range slider constants (linear semitone mapping)
_PITCH_SEMI_MIN = -39  # C1
_PITCH_SEMI_MAX = 39  # D#8


def _pitch_semi_to_frac(semi: int) -> float:
    """Map a semitone offset to 0..1 on a linear scale."""
    return (semi - _PITCH_SEMI_MIN) / (_PITCH_SEMI_MAX - _PITCH_SEMI_MIN)


def _pitch_frac_to_semi(frac: float) -> int:
    """Map 0..1 back to a semitone offset (rounded to nearest int)."""
    frac = max(0.0, min(1.0, frac))
    return round(_PITCH_SEMI_MIN + frac * (_PITCH_SEMI_MAX - _PITCH_SEMI_MIN))


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

    # Scroll / layout
    TITLE_AREA_HEIGHT = 60  # fixed title area at top
    BACK_AREA_HEIGHT = 70  # fixed back-button area at bottom
    SCROLL_SPEED = 30
    TOUCH_SCROLL_DEAD_ZONE = 10  # px of vertical movement before scroll activates

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
        self._pitch_range_hit_rect: pygame.Rect | None = None
        self._pitch_auto_rect: pygame.Rect | None = None
        self._scroll_y: int = 0  # scroll offset (positive = scrolled down)
        self._content_height: int = 0  # total content height (computed each frame)
        # Touch-drag scrolling state
        self._touch_start: tuple[int, int] | None = None  # (mx, my) at button-down
        self._touch_scrolling: bool = False  # True once drag exceeds dead zone
        self._touch_last_y: int = 0  # last y for computing delta

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

    # --- Pitch range slider helpers ---

    def _pitch_range_value_from_x(self, x: int) -> int:
        sx = self._content_left
        frac = max(0.0, min(1.0, (x - sx) / self.CONTENT_WIDTH))
        return _pitch_frac_to_semi(frac)

    def _set_pitch_range_value(self, handle: str, semi: int) -> None:
        semi = max(_PITCH_SEMI_MIN, min(_PITCH_SEMI_MAX, semi))
        if handle == "pitch_min":
            self.settings.pitch_note_min = semi
        else:
            self.settings.pitch_note_max = semi
        self.settings.validate_and_clamp()
        self.settings.save()

    # --- Scroll helpers ---

    def _max_scroll(self) -> int:
        """Maximum scroll offset (0 if content fits)."""
        viewport = SCREEN_HEIGHT - self.TITLE_AREA_HEIGHT - self.BACK_AREA_HEIGHT
        return max(0, self._content_height - viewport)

    def _clamp_scroll(self) -> None:
        self._scroll_y = max(0, min(self._max_scroll(), self._scroll_y))

    # --- Event handling ---

    def _is_on_slider(self, mx: int, my: int) -> bool:
        """Check if a point is on any slider hit rect."""
        for rect in self._slider_rects.values():
            if rect.collidepoint(mx, my):
                return True
        if self._range_hit_rect and self._range_hit_rect.collidepoint(mx, my):
            return True
        if self._pitch_range_hit_rect and self._pitch_range_hit_rect.collidepoint(mx, my):
            return True
        return False

    def _handle_tap(self, mx: int, my: int) -> None:
        """Process a tap/click at the given position (no drag occurred)."""
        if self._back_rect and self._back_rect.collidepoint(mx, my):
            self.on_back()
            return

        if self._pitch_auto_rect and self._pitch_auto_rect.collidepoint(mx, my):
            self.settings.pitch_range_auto = not self.settings.pitch_range_auto
            self.settings.save()
            return

        # Start slider interaction from tap position
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

        if self._pitch_range_hit_rect and self._pitch_range_hit_rect.collidepoint(mx, my):
            min_frac = _pitch_semi_to_frac(self.settings.pitch_note_min)
            max_frac = _pitch_semi_to_frac(self.settings.pitch_note_max)
            sx = self._content_left
            min_x = sx + min_frac * self.CONTENT_WIDTH
            max_x = sx + max_frac * self.CONTENT_WIDTH
            if abs(mx - min_x) <= abs(mx - max_x):
                self._dragging = "pitch_min"
            else:
                self._dragging = "pitch_max"
            self._set_pitch_range_value(self._dragging, self._pitch_range_value_from_x(mx))
            return

        for key, rect in self._slider_rects.items():
            if rect.collidepoint(mx, my):
                self._dragging = key
                all_sliders = _GENERAL_SLIDERS + _LEVEL_SLIDERS
                for slider in all_sliders:
                    if slider.key == key:
                        self._set_value(slider, self._value_from_x(slider, mx))
                        break
                break

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            self._scroll_y -= event.y * self.SCROLL_SPEED
            self._clamp_scroll()
            return

        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self._back_hovered = bool(self._back_rect and self._back_rect.collidepoint(mx, my))

            # Touch-drag scrolling
            if self._touch_start is not None and not self._dragging:
                dy = my - self._touch_start[1]
                if self._touch_scrolling:
                    delta = my - self._touch_last_y
                    self._scroll_y -= delta
                    self._clamp_scroll()
                    self._touch_last_y = my
                    return
                elif abs(dy) > self.TOUCH_SCROLL_DEAD_ZONE:
                    self._touch_scrolling = True
                    self._touch_last_y = my
                    return

            # Hover detection (for mouse users)
            self._hovered_slider = None
            for key, rect in self._slider_rects.items():
                if rect.collidepoint(mx, my):
                    self._hovered_slider = key
            if self._range_hit_rect and self._range_hit_rect.collidepoint(mx, my):
                min_frac = _freq_to_frac(self.settings.overtone_freq_min)
                max_frac = _freq_to_frac(self.settings.overtone_freq_max)
                sx = self._content_left
                min_x = sx + min_frac * self.CONTENT_WIDTH
                max_x = sx + max_frac * self.CONTENT_WIDTH
                if abs(mx - min_x) <= abs(mx - max_x):
                    self._hovered_slider = "range_min"
                else:
                    self._hovered_slider = "range_max"
            if self._pitch_range_hit_rect and self._pitch_range_hit_rect.collidepoint(mx, my):
                min_frac = _pitch_semi_to_frac(self.settings.pitch_note_min)
                max_frac = _pitch_semi_to_frac(self.settings.pitch_note_max)
                sx = self._content_left
                min_x = sx + min_frac * self.CONTENT_WIDTH
                max_x = sx + max_frac * self.CONTENT_WIDTH
                if abs(mx - min_x) <= abs(mx - max_x):
                    self._hovered_slider = "pitch_min"
                else:
                    self._hovered_slider = "pitch_max"

            # Handle slider drag (only when not touch-scrolling)
            if self._dragging:
                if self._dragging in ("range_min", "range_max"):
                    self._set_range_value(self._dragging, self._range_value_from_x(mx))
                elif self._dragging in ("pitch_min", "pitch_max"):
                    self._set_pitch_range_value(self._dragging, self._pitch_range_value_from_x(mx))
                else:
                    all_sliders = _GENERAL_SLIDERS + _LEVEL_SLIDERS
                    for slider in all_sliders:
                        if slider.key == self._dragging:
                            self._set_value(slider, self._value_from_x(slider, mx))
                            break

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # Back button is outside scrollable area — handle immediately
            if self._back_rect and self._back_rect.collidepoint(mx, my):
                self.on_back()
                return
            # If touch lands on a slider, start slider drag immediately
            # (horizontal slider drags shouldn't trigger scroll)
            if self._is_on_slider(mx, my):
                self._handle_tap(mx, my)
                return
            # Otherwise, start tracking for potential touch-scroll gesture
            self._touch_start = (mx, my)
            self._touch_scrolling = False

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            mx, my = event.pos
            was_scrolling = self._touch_scrolling
            self._touch_start = None
            self._touch_scrolling = False
            if self._dragging:
                self._dragging = None
            elif not was_scrolling:
                # It was a tap (no scroll happened) — process as click
                self._handle_tap(mx, my)

    def update(self, dt: float) -> None:
        pass

    # --- Drawing ---

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        surface.fill(COLOR_BG)
        self._slider_rects.clear()
        self._range_hit_rect = None
        self._pitch_range_hit_rect = None
        self._pitch_auto_rect = None

        sx = self._content_left

        # --- Fixed title area ---
        title = self._font_title.render("Settings", True, COLOR_TEXT)
        title_rect = title.get_rect(centerx=SCREEN_WIDTH // 2, top=10)
        surface.blit(title, title_rect)
        title_bottom = self.TITLE_AREA_HEIGHT - 4
        right = sx + self.CONTENT_WIDTH
        pygame.draw.line(surface, COLOR_DIVIDER, (sx, title_bottom), (right, title_bottom))

        # --- Scrollable content area ---
        scroll_top = self.TITLE_AREA_HEIGHT
        scroll_bottom = SCREEN_HEIGHT - self.BACK_AREA_HEIGHT
        clip_rect = pygame.Rect(0, scroll_top, SCREEN_WIDTH, scroll_bottom - scroll_top)
        surface.set_clip(clip_rect)

        # y is in content-space; screen_y = scroll_top + y - scroll_y
        y = 0  # content y
        offset = scroll_top - self._scroll_y  # content-to-screen offset

        y += 6  # small gap after title divider

        # Group 1: General
        y = self._draw_group_heading(surface, "General", y + offset) - offset
        for slider in _GENERAL_SLIDERS:
            y = self._draw_slider(surface, slider, y + offset) - offset
        y += self.GROUP_GAP
        line_sy = y + offset
        pygame.draw.line(surface, COLOR_DIVIDER, (sx, line_sy), (sx + self.CONTENT_WIDTH, line_sy))
        y += self.GROUP_GAP

        # Group 2: Sound Levels
        y = self._draw_group_heading(surface, "Sound Levels", y + offset) - offset
        for slider in _LEVEL_SLIDERS:
            y = self._draw_slider(surface, slider, y + offset) - offset
        y += self.GROUP_GAP
        line_sy = y + offset
        pygame.draw.line(surface, COLOR_DIVIDER, (sx, line_sy), (sx + self.CONTENT_WIDTH, line_sy))
        y += self.GROUP_GAP

        # Group 3: Overtones (range slider)
        y = self._draw_group_heading(surface, "Overtones", y + offset) - offset
        y = self._draw_range_slider(surface, y + offset) - offset
        y += self.GROUP_GAP
        line_sy = y + offset
        pygame.draw.line(surface, COLOR_DIVIDER, (sx, line_sy), (sx + self.CONTENT_WIDTH, line_sy))
        y += self.GROUP_GAP

        # Group 4: Pitch
        y = self._draw_group_heading(surface, "Pitch", y + offset) - offset
        y = self._draw_pitch_auto_toggle(surface, y + offset) - offset
        y = self._draw_pitch_range_slider(surface, y + offset) - offset

        self._content_height = y + self.GROUP_GAP
        self._clamp_scroll()

        surface.set_clip(None)

        # --- Scrollbar indicator (if content overflows) ---
        max_scr = self._max_scroll()
        if max_scr > 0:
            viewport_h = scroll_bottom - scroll_top
            bar_h = max(20, int(viewport_h * viewport_h / self._content_height))
            bar_y = scroll_top + int(self._scroll_y / max_scr * (viewport_h - bar_h))
            bar_x = SCREEN_WIDTH - 6
            pygame.draw.rect(surface, (80, 80, 100), (bar_x, bar_y, 4, bar_h), border_radius=2)

        # --- Fixed back-button area ---
        pygame.draw.rect(surface, COLOR_BG, (0, scroll_bottom, SCREEN_WIDTH, self.BACK_AREA_HEIGHT))
        bx = (SCREEN_WIDTH - self.BACK_BUTTON_WIDTH) // 2
        by = scroll_bottom + (self.BACK_AREA_HEIGHT - self.BACK_BUTTON_HEIGHT) // 2
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

    def _draw_pitch_auto_toggle(self, surface: pygame.Surface, y: int) -> int:
        sx = self._content_left
        is_auto = self.settings.pitch_range_auto

        label = self._font_label.render("Chart Range", True, COLOR_TEXT)
        surface.blit(label, (sx, y))

        # Toggle button: [Auto] / [Fixed]
        btn_text = "Auto" if is_auto else "Fixed"
        btn_surf = self._font_value.render(btn_text, True, COLOR_SLIDER_FILL)
        btn_w = btn_surf.get_width() + 20
        btn_h = 28
        btn_x = sx + self.CONTENT_WIDTH - btn_w
        btn_y = y + (label.get_height() - btn_h) // 2
        btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        self._pitch_auto_rect = btn_rect

        bg = COLOR_SLIDER_FILL if is_auto else COLOR_BUTTON_BG
        pygame.draw.rect(surface, bg, btn_rect, border_radius=4)
        # Text color: dark on bright bg when auto, light otherwise
        text_color = COLOR_BG if is_auto else COLOR_SLIDER_FILL
        btn_label = self._font_value.render(btn_text, True, text_color)
        surface.blit(btn_label, btn_label.get_rect(center=btn_rect.center))
        pygame.draw.rect(surface, COLOR_SLIDER_FILL, btn_rect, 1, border_radius=4)

        return y + 36

    def _draw_pitch_range_slider(self, surface: pygame.Surface, y: int) -> int:
        sx = self._content_left
        semi_min = self.settings.pitch_note_min
        semi_max = self.settings.pitch_note_max
        frac_min = _pitch_semi_to_frac(semi_min)
        frac_max = _pitch_semi_to_frac(semi_max)

        is_min_active = self._dragging == "pitch_min"
        is_max_active = self._dragging == "pitch_max"
        is_min_hovered = self._hovered_slider == "pitch_min"
        is_max_hovered = self._hovered_slider == "pitch_max"

        # Label + current range value
        label = self._font_label.render("Note Range", True, COLOR_TEXT)
        surface.blit(label, (sx, y))
        range_str = (
            f"{note_name_from_semitone(semi_min)} \u2013 {note_name_from_semitone(semi_max)}"
        )
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
        self._pitch_range_hit_rect = pygame.Rect(
            sx - self.HANDLE_RADIUS,
            track_y - 16,
            self.CONTENT_WIDTH + self.HANDLE_RADIUS * 2,
            self.SLIDER_HEIGHT + 32,
        )

        # Range hints (note names at extremes)
        lo = self._font_hint.render(note_name_from_semitone(_PITCH_SEMI_MIN), True, COLOR_LABEL_DIM)
        hi = self._font_hint.render(note_name_from_semitone(_PITCH_SEMI_MAX), True, COLOR_LABEL_DIM)
        hint_y = track_y + self.SLIDER_HEIGHT + 4
        surface.blit(lo, (sx, hint_y))
        surface.blit(hi, (sx + self.CONTENT_WIDTH - hi.get_width(), hint_y))

        return y + self.SLIDER_ROW_HEIGHT
