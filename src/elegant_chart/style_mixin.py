# elegant_chart/style_mixin.py
from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

from matplotlib import font_manager

from ._paths import BUNDLED_FONT_FILES, FONTS_DIR


# Base font sizes in points, authored at REFERENCE_FIGSIZE; scaled via _ts()/_fs().
TYPE_SCALE = {
    "title": 18,  # spec 16-18pt (kept at top of range)
    "subtitle": 13,  # spec 12-13pt
    "axis_label": 10,  # spec 9-10pt
    "tick_label": 10,  # spec 9-10pt
    "legend": 10,  # aligned to data-label tier
    "value_label": 8,  # compact data labels
    "caption": 8,  # spec source/footnote 8pt
    "annotation": 10,  # axis-label tier, muted in-plot text
}

# Leading ratio applied to multi-line title/subtitle/caption text.
LINESPACING = 1.25

# Stable, named structural roles bound to palette[0..n] by index. Charts assign
# series colors by role (via _series_color) rather than a bare index-cycling
# `palette[idx % len(palette)]`, so color intent is explicit and overridable.
ROLE_NAMES = ("primary", "secondary", "tertiary", "quaternary", "quinary")


@dataclass(frozen=True)
class Theme:
    """A named visual theme: series palette plus canvas colors.

    ``dark`` selects the complementary set of text/axis/spine colors applied
    in :meth:`StyleMixin._apply_base_style`.
    """

    palette: Tuple[str, ...]
    grid_color: str
    bg_color: str
    dark: bool


# Registered themes, keyed by the name passed to ``ElegantChart(theme=...)``.
# Adding a theme is a one-entry addition here — no branching logic to edit.
THEMES: Dict[str, Theme] = {
    "consulting_light": Theme(
        palette=("#64D2FF", "#0097A7", "#6FE8FF", "#00BCD4", "#4FC3F7"),
        grid_color="#DDDDDD",
        bg_color="#FFFFFF",
        dark=False,
    ),
    "newsroom_muted": Theme(
        palette=("#3B5C92", "#8C4A5A", "#4E7B63", "#9467BD", "#B5893F"),
        grid_color="#E0E0E0",
        bg_color="#FAFAFA",
        dark=False,
    ),
    "consulting_dark": Theme(
        palette=("#8FB3FF", "#FF8C99", "#7AD8A0", "#B4A5FF", "#F5D27C"),
        grid_color="#333333",
        bg_color="#111827",
        dark=True,
    ),
    "newsroom_dark": Theme(
        # Fixed: was [("#6FE8FF", "#0097A7")] — a tuple inside a list, not a flat palette.
        palette=("#4C72B0", "#C44E52", "#55A868", "#8172B2", "#CCB974"),
        grid_color="#444444",
        bg_color="#0b1014",
        dark=True,
    ),
}

# Fallback theme for an unrecognised ``theme=`` name.
DEFAULT_THEME = "consulting_light"


class StyleMixin:
    def _fs(self, base: float) -> float:
        """Font size in points, scaled by font_scale and capped at the reference figure size."""
        return base * self.font_scale * min(self._figure_scale, 1.0)  # type: ignore[attr-defined]

    def _ts(self, name: str) -> float:
        """Scaled font size in points for a named type-scale role (see TYPE_SCALE)."""
        return self._fs(TYPE_SCALE[name])

    def _px(self, base: float) -> float:
        """Geometric point value (linewidth, markersize, pad …) scaled by figure size only."""
        return base * self._figure_scale  # type: ignore[attr-defined]

    def _register_fonts(self) -> None:
        """Register the bundled SF Pro fonts, plus any project-local overrides.

        Bundled fonts are resolved relative to the installed package
        (``elegant_chart/assets/fonts/``) so they are found regardless of the
        caller's working directory. A ``fonts/`` directory relative to the
        current working directory is also checked, letting a project supply
        its own SF Pro files (e.g. licensed copies) without rebuilding the
        package — those take precedence because they are registered last.
        """
        candidates = [FONTS_DIR / name for name in BUNDLED_FONT_FILES]
        candidates += [Path("fonts") / name for name in BUNDLED_FONT_FILES]

        for path in candidates:
            try:
                font_manager.fontManager.addfont(str(path))
            except (OSError, FileNotFoundError):
                pass

    def _configure_fonts(self) -> None:
        """Set font families, falling back to the system sans-serif if SF Pro is absent."""
        available = {f.name for f in font_manager.fontManager.ttflist}

        has_sf_pro = "SF Pro" in available
        has_sf_text = "SF Pro Text" in available
        has_sf_display = "SF Pro Display" in available

        if not (has_sf_pro or has_sf_text or has_sf_display):
            warnings.warn(
                "SF Pro fonts not found — falling back to system sans-serif. "
                "Place SF Pro .ttf/.otf files in a fonts/ directory to use them.",
                UserWarning,
                stacklevel=3,
            )

        self.font_main_family = "SF Pro" if has_sf_pro else "sans-serif"  # type: ignore[attr-defined]
        self.font_title_family = "SF Pro Text" if has_sf_text else "sans-serif"  # type: ignore[attr-defined]
        self.font_title_weight = "bold"  # type: ignore[attr-defined]
        self.font_caption_family = "SF Pro Display" if has_sf_display else "sans-serif"  # type: ignore[attr-defined]
        self.font_caption_weight = "light"  # type: ignore[attr-defined]

    def _apply_base_style(self) -> None:
        self._register_fonts()
        self._configure_fonts()

        theme = self.theme  # type: ignore[attr-defined]

        theme_def = THEMES.get(theme)
        if theme_def is None:
            warnings.warn(
                f"Unknown theme {theme!r} — falling back to {DEFAULT_THEME!r}. "
                f"Available themes: {', '.join(sorted(THEMES))}.",
                UserWarning,
                stacklevel=3,
            )
            theme_def = THEMES[DEFAULT_THEME]

        self.palette = list(theme_def.palette)  # type: ignore[attr-defined]
        self.grid_color = theme_def.grid_color  # type: ignore[attr-defined]
        self.bg_color = theme_def.bg_color  # type: ignore[attr-defined]
        dark = theme_def.dark

        if dark:
            self.color_axes_edge = "#f0f0f0"  # type: ignore[attr-defined]
            self.color_axes_label = "#f0f0f0"  # type: ignore[attr-defined]
            self.color_text_main = "#f0f0f0"  # type: ignore[attr-defined]
            self.color_tick = "#E5E7EB"  # type: ignore[attr-defined]
            self.color_title = "#f0f0f0"  # type: ignore[attr-defined]
            self.color_subtitle = "#999999"  # type: ignore[attr-defined]
            self.color_caption = "#999999"  # type: ignore[attr-defined]
            self.color_annotation = "#999999"  # type: ignore[attr-defined]
            self.color_spine = "#E5E7EB"  # type: ignore[attr-defined]
        else:
            self.color_axes_edge = "#444444"  # type: ignore[attr-defined]
            self.color_axes_label = "#222222"  # type: ignore[attr-defined]
            self.color_text_main = "#111111"  # type: ignore[attr-defined]
            self.color_tick = "#333333"  # type: ignore[attr-defined]
            self.color_title = "#111111"  # type: ignore[attr-defined]
            self.color_subtitle = "#666666"  # type: ignore[attr-defined]
            self.color_caption = "#555555"  # type: ignore[attr-defined]
            self.color_annotation = "#555555"  # type: ignore[attr-defined]
            self.color_spine = "#000000"  # type: ignore[attr-defined]

        # Bind ROLE_NAMES to this theme's palette by position, e.g.
        # {"primary": palette[0], "secondary": palette[1], ...}. Consumed by
        # _series_color() so series colors are explicit roles, not a bare cycle.
        self.color_roles = {  # type: ignore[attr-defined]
            name: self.palette[i % len(self.palette)]  # type: ignore[attr-defined]
            for i, name in enumerate(ROLE_NAMES)
        }

        dpi = getattr(self, "dpi", 150)
        self._rc.update(  # type: ignore[attr-defined]
            {
                "figure.dpi": dpi,
                "font.family": self.font_main_family,
                "axes.titlesize": self._ts("title"),
                "axes.labelsize": self._ts("axis_label"),
                "xtick.labelsize": self._ts("tick_label"),
                "ytick.labelsize": self._ts("tick_label"),
                "axes.edgecolor": self.color_axes_edge,
                "axes.labelcolor": self.color_axes_label,
                "text.color": self.color_text_main,
                "xtick.color": self.color_tick,
                "ytick.color": self.color_tick,
                "figure.facecolor": self.bg_color,
                "axes.facecolor": self.bg_color,
                "savefig.facecolor": self.bg_color,
            }
        )

    def _series_color(self, idx: int, label: Optional[str] = None) -> str:
        """Resolve a series' color: explicit ``color_map`` override, else by role.

        ``self.color_map`` (an optional ``{label: role_or_hex}`` dict set at
        construction) lets a caller pin a specific series to a named role
        (e.g. ``{"Resorts": "primary"}``) or a literal hex code. Series without
        an entry fall back to their positional role — ``ROLE_NAMES[idx]`` —
        which keeps unconfigured charts visually identical to a plain
        index-cycle while making the assignment an explicit, named mapping.
        """
        color_map: dict = getattr(self, "color_map", None) or {}
        if label is not None and label in color_map:
            value = color_map[label]
            return self.color_roles.get(value, value)  # type: ignore[attr-defined]

        role = ROLE_NAMES[idx % len(ROLE_NAMES)]
        return self.color_roles.get(role, self.palette[idx % len(self.palette)])  # type: ignore[attr-defined]
