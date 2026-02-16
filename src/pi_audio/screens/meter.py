import math
from pathlib import Path

import numpy as np
import pygame

from pi_audio.config import (
    BLOCK_SIZE,
    COLOR_BG,
    COLOR_BUTTON_BG,
    COLOR_BUTTON_HOVER,
    COLOR_CHART_BG,
    COLOR_GREEN,
    COLOR_GRID,
    COLOR_LABEL_DIM,
    COLOR_PITCH,
    COLOR_RED,
    COLOR_SLIDER_FILL,
    COLOR_TEXT,
    COLOR_YELLOW,
    FFT_SIZE,
    SAMPLE_RATE,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SPL_MAX,
    SPL_MIN,
)
from pi_audio.pitch import freq_to_note
from pi_audio.screens.base import Screen
from pi_audio.settings import Settings
from pi_audio.spectrogram import SpectrogramRenderer


class MeterScreen(Screen):
    # Layout
    READOUT_HEIGHT = 110
    CHART_LEFT_SPL = 80  # left margin when SPL y-axis labels are needed
    CHART_LEFT_SPEC = 50  # left margin for spectrogram freq labels
    CHART_LEFT_PITCH = 50  # left margin for pitch note labels
    CHART_RIGHT = 20
    CHART_BOTTOM = 40
    CHART_BOTTOM_SPEC = 10  # less bottom margin when no time labels
    CHART_BOTTOM_PITCH = 10

    # Toggle button dimensions (match hamburger menu sizing/margin)
    TOGGLE_SIZE = 40
    TOGGLE_MARGIN = 10
    TOGGLE_GAP = 8

    # Hamburger menu dimensions
    MENU_ICON_SIZE = 40
    MENU_ICON_MARGIN = 10
    MENU_DROPDOWN_WIDTH = 160
    MENU_ITEM_HEIGHT = 44

    # Pause button dimensions
    PAUSE_SIZE = 60

    # Pitch chart constants
    PITCH_OCTAVES_VISIBLE = 2.0  # how many octaves to show at once

    # All panel names in toggle order
    _PANEL_NAMES = ["overtones", "meter", "pitch"]

    def __init__(self, settings: Settings, on_settings: callable):
        self.settings = settings
        self.on_settings = on_settings
        self._spl: float = 0.0
        self._history: list[float] = []
        self._spectrogram: list[np.ndarray] = []
        self._pitch: float | None = None
        self._pitch_history: list[float | None] = []
        self._paused: bool = False
        self._pause_btn_rect: pygame.Rect | None = None
        self._spec_renderer = SpectrogramRenderer(
            SAMPLE_RATE,
            BLOCK_SIZE,
            freq_min=settings.overtone_freq_min,
            freq_max=settings.overtone_freq_max,
            fft_size=FFT_SIZE,
        )
        self._font_large: pygame.font.Font | None = None
        self._font_medium: pygame.font.Font | None = None
        self._font_small: pygame.font.Font | None = None
        self._font_icon: pygame.font.Font | None = None
        self._font_value_only: pygame.font.Font | None = None
        self._font_pitch_large: pygame.font.Font | None = None
        self._font_pitch_cents: pygame.font.Font | None = None
        self._toggle_btn_rects: dict[str, pygame.Rect] = {}
        self._icon_overtones: pygame.Surface | None = None
        self._icon_meter: pygame.Surface | None = None
        self._icon_pitch: pygame.Surface | None = None
        self._menu_icon_rect: pygame.Rect | None = None
        self._menu_open: bool = False
        self._menu_settings_rect: pygame.Rect | None = None
        self._menu_help_rect: pygame.Rect | None = None
        self._menu_exit_rect: pygame.Rect | None = None
        self._hovered_menu_item: str | None = None
        self._help_open: bool = False
        self._help_close_rect: pygame.Rect | None = None

    def _ensure_fonts(self) -> None:
        if self._font_large is None:
            self._font_large = pygame.font.SysFont("monospace", 120, bold=True)
            self._font_medium = pygame.font.SysFont("monospace", 28)
            self._font_small = pygame.font.SysFont("monospace", 18)
            self._font_icon = pygame.font.SysFont("monospace", 20)
            self._font_value_only = pygame.font.SysFont("monospace", 260, bold=True)
            self._font_pitch_large = pygame.font.SysFont("monospace", 120, bold=True)
            self._font_pitch_cents = pygame.font.SysFont("monospace", 32)
            # Load toggle button icons
            assets = Path(__file__).resolve().parent.parent / "assets"
            sz = self.TOGGLE_SIZE - 4  # leave room for border
            self._icon_overtones = pygame.transform.smoothscale(
                pygame.image.load(str(assets / "icon_overtones.png")).convert(), (sz, sz)
            )
            self._icon_meter = pygame.transform.smoothscale(
                pygame.image.load(str(assets / "icon_meter.png")).convert(), (sz, sz)
            )
            self._icon_pitch = pygame.transform.smoothscale(
                pygame.image.load(str(assets / "icon_pitch.png")).convert(), (sz, sz)
            )

    def set_audio_data(
        self,
        spl: float,
        history: list[float],
        spectrogram: list[np.ndarray] | None = None,
        pitch: float | None = None,
        pitch_history: list[float | None] | None = None,
    ) -> None:
        self._spl = spl
        self._pitch = pitch
        if not self._paused:
            self._history = history
            if spectrogram is not None:
                self._spectrogram = spectrogram
            if pitch_history is not None:
                self._pitch_history = pitch_history

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEMOTION:
            self._hovered_menu_item = None
            if self._menu_open:
                if self._menu_settings_rect and self._menu_settings_rect.collidepoint(event.pos):
                    self._hovered_menu_item = "settings"
                elif self._menu_help_rect and self._menu_help_rect.collidepoint(event.pos):
                    self._hovered_menu_item = "help"
                elif self._menu_exit_rect and self._menu_exit_rect.collidepoint(event.pos):
                    self._hovered_menu_item = "exit"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._help_open:
                self._help_open = False
                return
            if self._menu_open:
                if self._menu_settings_rect and self._menu_settings_rect.collidepoint(event.pos):
                    self._menu_open = False
                    self.on_settings()
                elif self._menu_help_rect and self._menu_help_rect.collidepoint(event.pos):
                    self._menu_open = False
                    self._help_open = True
                elif self._menu_exit_rect and self._menu_exit_rect.collidepoint(event.pos):
                    raise SystemExit
                else:
                    self._menu_open = False
            elif self._pause_btn_rect and self._pause_btn_rect.collidepoint(event.pos):
                self._paused = not self._paused
            elif self._menu_icon_rect and self._menu_icon_rect.collidepoint(event.pos):
                self._menu_open = True
            else:
                # Check toggle buttons
                for name, rect in self._toggle_btn_rects.items():
                    if rect.collidepoint(event.pos):
                        self._toggle_panel(name)
                        break

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface: pygame.Surface) -> None:
        self._ensure_fonts()
        surface.fill(COLOR_BG)
        panels = self.settings.active_panels
        if len(panels) > 0:
            self._draw_readout(surface)
            self._draw_chart(surface)
            self._draw_pause_button(surface)
        else:
            self._draw_value_only(surface)
        self._draw_toggle_buttons(surface)
        self._draw_menu(surface)
        if self._help_open:
            self._draw_help_modal(surface)

    def _spl_color(self, db: float) -> tuple[int, int, int]:
        """Determine color based on SPL level and current thresholds."""
        if db < self.settings.quiet_threshold:
            return COLOR_GREEN
        elif db < self.settings.moderate_threshold:
            return COLOR_YELLOW
        else:
            return COLOR_RED

    def _toggle_panel(self, name: str) -> None:
        """Toggle a panel on/off, enforcing max 2 active panels."""
        panels = list(self.settings.active_panels)
        if name in panels:
            # Turning off
            panels.remove(name)
        else:
            # Turning on
            if len(panels) >= 2:
                # Auto-deactivate the leftmost active panel
                panels.pop(0)
            panels.append(name)

        self.settings.active_panels = panels
        self.settings.save()
        if len(panels) == 0:
            self._paused = False
            self._pause_btn_rect = None

    def _draw_toggle_buttons(self, surface: pygame.Surface) -> None:
        """Draw three toggle buttons in the upper-left corner using icon images."""
        panels = self.settings.active_panels
        icons = {
            "overtones": self._icon_overtones,
            "meter": self._icon_meter,
            "pitch": self._icon_pitch,
        }

        x = self.TOGGLE_MARGIN
        y = self.TOGGLE_MARGIN
        sz = self.TOGGLE_SIZE

        self._toggle_btn_rects.clear()
        for i, name in enumerate(self._PANEL_NAMES):
            on = name in panels
            icon = icons.get(name)

            bx = x + i * (sz + self.TOGGLE_GAP)
            rect = pygame.Rect(bx, y, sz, sz)
            self._toggle_btn_rects[name] = rect

            # Background fill
            bg = COLOR_SLIDER_FILL if on else COLOR_BUTTON_BG
            pygame.draw.rect(surface, bg, rect, border_radius=4)

            # Blit the icon image centered in the button
            if icon is not None:
                ix = bx + (sz - icon.get_width()) // 2
                iy = y + (sz - icon.get_height()) // 2
                surface.blit(icon, (ix, iy))

            # Dim overlay when off
            if not on:
                dim = pygame.Surface((sz, sz), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 140))
                surface.blit(dim, (bx, y))

            # Border
            border_color = COLOR_SLIDER_FILL if on else COLOR_GRID
            pygame.draw.rect(surface, border_color, rect, 2, border_radius=4)

    def _draw_pause_button(self, surface: pygame.Surface) -> None:
        """Draw pause/play button near the upper-right, left of the hamburger menu."""
        sz = self.PAUSE_SIZE
        menu_left = SCREEN_WIDTH - self.MENU_ICON_SIZE - self.MENU_ICON_MARGIN
        bx = menu_left - sz - 12
        by = (self.READOUT_HEIGHT - sz) // 2
        self._pause_btn_rect = pygame.Rect(bx, by, sz, sz)

        # Button background
        bg = COLOR_BUTTON_BG
        pygame.draw.rect(surface, bg, self._pause_btn_rect, border_radius=6)
        pygame.draw.rect(surface, COLOR_GRID, self._pause_btn_rect, 2, border_radius=6)

        cx = bx + sz // 2
        cy = by + sz // 2

        if self._paused:
            # Play triangle
            tri_h = sz * 0.5
            tri_w = tri_h * 0.8
            points = [
                (cx - tri_w // 2 + 2, cy - tri_h // 2),
                (cx - tri_w // 2 + 2, cy + tri_h // 2),
                (cx + tri_w // 2 + 2, cy),
            ]
            pygame.draw.polygon(surface, COLOR_TEXT, points)
        else:
            # Pause bars
            bar_h = int(sz * 0.45)
            bar_w = int(sz * 0.12)
            gap = int(sz * 0.1)
            pygame.draw.rect(
                surface,
                COLOR_TEXT,
                (cx - gap - bar_w, cy - bar_h // 2, bar_w, bar_h),
            )
            pygame.draw.rect(
                surface,
                COLOR_TEXT,
                (cx + gap, cy - bar_h // 2, bar_w, bar_h),
            )

    def _draw_value_only(self, surface: pygame.Surface) -> None:
        """Draw the SPL and pitch as large centered values when no panels are active."""
        cy = SCREEN_HEIGHT // 2

        # SPL value (large, left-center)
        color = self._spl_color(self._spl)
        spl_text = f"{self._spl:.1f}"
        spl_surf = self._font_value_only.render(spl_text, True, color)
        spl_rect = spl_surf.get_rect(centerx=SCREEN_WIDTH // 2, centery=cy - 40)
        surface.blit(spl_surf, spl_rect)

        # dB(A) label
        label = self._font_medium.render("dB(A)", True, COLOR_LABEL_DIM)
        surface.blit(label, label.get_rect(centerx=SCREEN_WIDTH // 2, top=spl_rect.bottom + 2))

        # Pitch value below
        if self._pitch is not None:
            note_name, octave, cents = freq_to_note(self._pitch)
            note_text = f"{note_name}{octave}"
            note_surf = self._font_value_only.render(note_text, True, COLOR_PITCH)
            cents_text = f"+{cents}" if cents >= 0 else f"{cents}"
            if abs(cents) <= 10:
                cents_color = COLOR_GREEN
            elif abs(cents) <= 25:
                cents_color = COLOR_YELLOW
            else:
                cents_color = COLOR_RED
            cents_surf = self._font_large.render(cents_text, True, cents_color)
            # Position as a group
            total_w = note_surf.get_width() + 10 + cents_surf.get_width()
            note_rect = note_surf.get_rect(centery=cy + spl_rect.height // 2 + 60)
            note_rect.left = (SCREEN_WIDTH - total_w) // 2
            surface.blit(note_surf, note_rect)
            cents_rect = cents_surf.get_rect(left=note_rect.right + 10, top=note_rect.top + 10)
            surface.blit(cents_surf, cents_rect)
        else:
            dash_surf = self._font_value_only.render("---", True, COLOR_LABEL_DIM)
            dash_rect = dash_surf.get_rect(
                centerx=SCREEN_WIDTH // 2, centery=cy + spl_rect.height // 2 + 60
            )
            surface.blit(dash_surf, dash_rect)

    def _draw_readout(self, surface: pygame.Surface) -> None:
        cy = self.READOUT_HEIGHT // 2 + 8  # extra top padding

        # Compute usable horizontal zone between toggle buttons and pause/menu
        num_toggles = len(self._PANEL_NAMES)
        zone_left = (
            self.TOGGLE_MARGIN + num_toggles * self.TOGGLE_SIZE
            + (num_toggles - 1) * self.TOGGLE_GAP + 10
        )
        menu_left = SCREEN_WIDTH - self.MENU_ICON_SIZE - self.MENU_ICON_MARGIN
        pause_left = menu_left - self.PAUSE_SIZE - 12
        zone_right = pause_left - 10

        # Render SPL text
        color = self._spl_color(self._spl)
        text = f"{self._spl:5.1f}"
        spl_surf = self._font_large.render(text, True, color)

        # Render pitch text to measure its width
        pitch_surf, cents_surf, cents_color = self._render_pitch_surfaces()
        pitch_w = 0
        if pitch_surf is not None:
            pitch_w = pitch_surf.get_width() + 4 + (cents_surf.get_width() if cents_surf else 0)
        else:
            pitch_w = self._font_pitch_large.render("---", True, COLOR_LABEL_DIM).get_width()

        # Position both with a minimum gap, centered in the zone as a group
        gap = 30
        total_w = spl_surf.get_width() + gap + pitch_w
        zone_cx = (zone_left + zone_right) // 2
        group_left = zone_cx - total_w // 2

        # Draw SPL
        spl_rect = spl_surf.get_rect(left=group_left, centery=cy)
        surface.blit(spl_surf, spl_rect)

        # Draw pitch
        pitch_left = spl_rect.right + gap
        self._draw_pitch_readout(surface, cy, pitch_left, pitch_surf, cents_surf, cents_color)

    def _render_pitch_surfaces(
        self,
    ) -> tuple[pygame.Surface | None, pygame.Surface | None, tuple | None]:
        """Pre-render pitch note and cents surfaces for measurement."""
        if self._pitch is None:
            return None, None, None
        note_name, octave, cents = freq_to_note(self._pitch)
        note_text = f"{note_name}{octave}"
        note_surf = self._font_pitch_large.render(note_text, True, COLOR_PITCH)
        cents_text = f"+{cents}" if cents >= 0 else f"{cents}"
        if abs(cents) <= 10:
            cents_color = COLOR_GREEN
        elif abs(cents) <= 25:
            cents_color = COLOR_YELLOW
        else:
            cents_color = COLOR_RED
        cents_surf = self._font_pitch_cents.render(cents_text, True, cents_color)
        return note_surf, cents_surf, cents_color

    def _draw_pitch_readout(
        self,
        surface: pygame.Surface,
        cy: int,
        left: int,
        note_surf: pygame.Surface | None,
        cents_surf: pygame.Surface | None,
        cents_color: tuple | None,
    ) -> None:
        """Draw pitch note name + cents deviation starting at the given left position."""

        if note_surf is not None:
            note_rect = note_surf.get_rect(left=left, centery=cy)
            surface.blit(note_surf, note_rect)
            cents_rect = cents_surf.get_rect(left=note_rect.right + 4, top=note_rect.top + 8)
            surface.blit(cents_surf, cents_rect)
        else:
            # No pitch detected
            dash_surf = self._font_pitch_large.render("---", True, COLOR_LABEL_DIM)
            dash_rect = dash_surf.get_rect(left=left, centery=cy)
            surface.blit(dash_surf, dash_rect)

    def _draw_chart(self, surface: pygame.Surface) -> None:
        chart_top = self.READOUT_HEIGHT + 5
        panels = self.settings.active_panels
        num_panels = len(panels)

        if num_panels == 1:
            # Single panel: full width
            panel = panels[0]
            left, bottom_margin = self._panel_margins(panel)
            chart_right = SCREEN_WIDTH - self.CHART_RIGHT
            chart_bottom = SCREEN_HEIGHT - bottom_margin
            chart_width = chart_right - left
            chart_height = chart_bottom - chart_top
            self._draw_panel(surface, panel, left, chart_top, chart_width, chart_height)

        elif num_panels == 2:
            # Two panels side-by-side
            gap = 60
            total_width = SCREEN_WIDTH - self._panel_margins(panels[0])[0] - self.CHART_RIGHT
            half = (total_width - gap) // 2

            # Left panel
            left_margin, bottom_margin_l = self._panel_margins(panels[0])
            chart_bottom_l = SCREEN_HEIGHT - bottom_margin_l
            height_l = chart_bottom_l - chart_top
            self._draw_panel(surface, panels[0], left_margin, chart_top, half, height_l)

            # Right panel
            right_left = left_margin + half + gap
            _, bottom_margin_r = self._panel_margins(panels[1])
            chart_bottom_r = SCREEN_HEIGHT - bottom_margin_r
            height_r = chart_bottom_r - chart_top
            self._draw_panel(
                surface, panels[1], right_left, chart_top, total_width - half - gap, height_r
            )

    def _panel_margins(self, panel: str) -> tuple[int, int]:
        """Return (left_margin, bottom_margin) for a given panel type."""
        if panel == "meter":
            return self.CHART_LEFT_SPL, self.CHART_BOTTOM
        elif panel == "overtones":
            return self.CHART_LEFT_SPEC, self.CHART_BOTTOM_SPEC
        else:  # pitch
            return self.CHART_LEFT_PITCH, self.CHART_BOTTOM_PITCH

    def _draw_panel(
        self, surface: pygame.Surface, panel: str, left: int, top: int, width: int, height: int
    ) -> None:
        if panel == "meter":
            self._draw_spl_chart(surface, left, top, width, height)
        elif panel == "overtones":
            self._draw_spectrogram(surface, left, top, width, height)
        elif panel == "pitch":
            self._draw_pitch_chart(surface, left, top, width, height)

    def _draw_spectrogram(
        self, surface: pygame.Surface, left: int, top: int, width: int, height: int
    ) -> None:
        # Sync freq range from settings
        self._spec_renderer.set_freq_range(
            self.settings.overtone_freq_min, self.settings.overtone_freq_max
        )
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

    def _draw_pitch_chart(
        self, surface: pygame.Surface, left: int, top: int, width: int, height: int
    ) -> None:
        """Draw a Melodyne-style piano-roll pitch history chart."""
        right = left + width
        bottom = top + height

        # Chart background
        pygame.draw.rect(surface, COLOR_CHART_BG, (left, top, width, height))

        # Determine Y-axis range based on recent pitch data
        valid_pitches = [p for p in self._pitch_history if p is not None]

        if len(valid_pitches) < 2:
            # Not enough data — draw empty chart
            pygame.draw.rect(surface, COLOR_GRID, (left, top, width, height), 1)
            no_data = self._font_small.render("Listening...", True, COLOR_LABEL_DIM)
            surface.blit(
                no_data,
                no_data.get_rect(center=(left + width // 2, top + height // 2)),
            )
            return

        # Compute range: center on median pitch, show ~2 octaves
        median_pitch = sorted(valid_pitches)[len(valid_pitches) // 2]
        # Convert to semitones from A4 for easier math
        median_semi = 12.0 * math.log2(median_pitch / 440.0) + 69  # MIDI note number
        half_range = self.PITCH_OCTAVES_VISIBLE * 12 / 2  # semitones
        semi_min = median_semi - half_range
        semi_max = median_semi + half_range
        semi_range = semi_max - semi_min

        # Draw semitone grid lines with note labels
        note_names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
        first_semi = int(math.ceil(semi_min))
        last_semi = int(math.floor(semi_max))

        for semi in range(first_semi, last_semi + 1):
            frac = (semi - semi_min) / semi_range
            y = bottom - int(frac * height)
            if y < top or y > bottom:
                continue

            note_idx = semi % 12
            is_natural = note_names[note_idx] in ("C", "D", "E", "F", "G", "A", "B")

            # Grid line: brighter for natural notes
            line_color = (60, 60, 75) if is_natural else (40, 40, 52)
            pygame.draw.line(surface, line_color, (left, y), (right, y))

            # Label for natural notes only (to avoid clutter)
            if is_natural:
                octave = semi // 12 - 1
                label_text = f"{note_names[note_idx]}{octave}"
                label = self._font_small.render(label_text, True, COLOR_LABEL_DIM)
                lx = left - label.get_width() - 6
                ly = y - label.get_height() // 2
                ly = max(top, min(bottom - label.get_height(), ly))
                surface.blit(label, (lx, ly))

        # Plot pitch trace
        n = len(self._pitch_history)
        history_len = max(self.settings.history_length, 1)
        prev_point = None

        for i, pitch in enumerate(self._pitch_history):
            if pitch is None:
                prev_point = None
                continue

            x = right - (n - 1 - i) / max(history_len - 1, 1) * width
            semi = 12.0 * math.log2(pitch / 440.0) + 69
            frac = (semi - semi_min) / semi_range
            y = bottom - frac * height

            cur_point = (x, y)
            if prev_point is not None:
                pygame.draw.line(surface, COLOR_PITCH, prev_point, cur_point, 2)
            else:
                # Draw a dot for isolated points
                pygame.draw.circle(surface, COLOR_PITCH, (int(x), int(y)), 2)
            prev_point = cur_point

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
            num_items = 3

            # Dropdown background
            dropdown_rect = pygame.Rect(
                dx, dy, self.MENU_DROPDOWN_WIDTH, self.MENU_ITEM_HEIGHT * num_items
            )
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

            # Help item
            hy = dy + self.MENU_ITEM_HEIGHT
            self._menu_help_rect = pygame.Rect(
                dx, hy, self.MENU_DROPDOWN_WIDTH, self.MENU_ITEM_HEIGHT
            )
            if self._hovered_menu_item == "help":
                pygame.draw.rect(surface, COLOR_BUTTON_HOVER, self._menu_help_rect)
            help_text = self._font_icon.render("Help", True, COLOR_TEXT)
            surface.blit(
                help_text,
                help_text.get_rect(midleft=(dx + 12, hy + self.MENU_ITEM_HEIGHT // 2)),
            )

            # Divider
            pygame.draw.line(
                surface,
                (80, 80, 100),
                (dx + 8, hy + self.MENU_ITEM_HEIGHT),
                (dx + self.MENU_DROPDOWN_WIDTH - 8, hy + self.MENU_ITEM_HEIGHT),
            )

            # Exit item
            ey = hy + self.MENU_ITEM_HEIGHT
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

    def _draw_help_modal(self, surface: pygame.Surface) -> None:
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surface.blit(overlay, (0, 0))

        # Modal box
        modal_w, modal_h = 700, 480
        mx = (SCREEN_WIDTH - modal_w) // 2
        my = (SCREEN_HEIGHT - modal_h) // 2
        modal_rect = pygame.Rect(mx, my, modal_w, modal_h)
        pygame.draw.rect(surface, (30, 30, 45), modal_rect, border_radius=8)
        pygame.draw.rect(surface, (80, 80, 100), modal_rect, 2, border_radius=8)

        font_title = pygame.font.SysFont("monospace", 28, bold=True)
        font_body = pygame.font.SysFont("monospace", 16)
        font_heading = pygame.font.SysFont("monospace", 18, bold=True)
        font_hint = pygame.font.SysFont("monospace", 14)

        pad = 24
        y = my + pad

        # Title
        title = font_title.render("pi-audio", True, COLOR_TEXT)
        surface.blit(title, (mx + pad, y))
        y += title.get_height() + 6

        desc = font_body.render(
            "A real-time sound level display for Raspberry Pi.", True, COLOR_LABEL_DIM
        )
        surface.blit(desc, (mx + pad, y))
        y += desc.get_height() + 16

        # Help content
        sections = [
            (
                "Spectrogram (Overtones)",
                [
                    "Shows a scrolling view of sound frequencies over",
                    "time using FFT analysis. Low frequencies at the",
                    "bottom, high at the top. Brighter colors = louder.",
                ],
            ),
            (
                "Level History (Meter)",
                [
                    "A rolling chart of the A-weighted sound pressure",
                    "level (dB) over time. Color indicates level:",
                    "green = safe, yellow = caution, red = loud.",
                ],
            ),
            (
                "Pitch Detection",
                [
                    "Detects the fundamental pitch of monophonic sound",
                    "using the YIN algorithm. Shows note name, octave,",
                    "and cents deviation. Piano-roll chart shows history.",
                ],
            ),
            (
                "Display Modes",
                [
                    "Use the toggle buttons (top-left) to show up to",
                    "two panels at once. Tap a third to auto-replace",
                    "the first active panel.",
                ],
            ),
        ]

        for heading, lines in sections:
            h = font_heading.render(heading, True, COLOR_SLIDER_FILL)
            surface.blit(h, (mx + pad, y))
            y += h.get_height() + 4
            for line in lines:
                t = font_body.render(line, True, COLOR_TEXT)
                surface.blit(t, (mx + pad + 12, y))
                y += t.get_height() + 2
            y += 8

        # Close hint
        hint = font_hint.render("Tap anywhere to close", True, COLOR_LABEL_DIM)
        surface.blit(hint, hint.get_rect(centerx=SCREEN_WIDTH // 2, bottom=my + modal_h - 14))
