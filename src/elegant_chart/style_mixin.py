# elegant_chart/style_mixin.py
from __future__ import annotations

import warnings

from matplotlib import font_manager


class StyleMixin:
    def _fs(self, base: float) -> float:
        return base * self.font_scale  # type: ignore[attr-defined]

    def _register_fonts(self) -> None:
        """Try to register bundled SF Pro fonts; silently skip on missing files."""
        candidates = [
            "fonts/SF-Pro.ttf",
            "fonts/SF-Pro-Display-Light.otf",
            "fonts/SF-Pro-Display-Medium.otf",
            "fonts/SF-Pro-Text-Bold.otf",
        ]
        for path in candidates:
            try:
                font_manager.fontManager.addfont(path)
            except OSError:
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

        if theme == "consulting_light":
            self.palette = ["#4C72B0", "#C44E52", "#55A868", "#8172B2", "#CCB974"]  # type: ignore[attr-defined]
            self.grid_color = "#DDDDDD"  # type: ignore[attr-defined]
            self.bg_color = "#FFFFFF"  # type: ignore[attr-defined]
            dark = False

        elif theme == "newsroom_muted":
            self.palette = ["#3B5C92", "#8C4A5A", "#4E7B63", "#9467BD", "#B5893F"]  # type: ignore[attr-defined]
            self.grid_color = "#E0E0E0"  # type: ignore[attr-defined]
            self.bg_color = "#FAFAFA"  # type: ignore[attr-defined]
            dark = False

        elif theme == "consulting_dark":
            self.palette = ["#8FB3FF", "#FF8C99", "#7AD8A0", "#B4A5FF", "#F5D27C"]  # type: ignore[attr-defined]
            self.grid_color = "#333333"  # type: ignore[attr-defined]
            self.bg_color = "#111827"  # type: ignore[attr-defined]
            dark = True

        elif theme == "newsroom_dark":
            # Fixed: was [("#6FE8FF", "#0097A7")] — a tuple inside a list, not a flat palette.
            self.palette = ["#64D2FF", "#0097A7", "#6FE8FF", "#00BCD4", "#4FC3F7"]  # type: ignore[attr-defined]
            self.grid_color = "#444444"  # type: ignore[attr-defined]
            self.bg_color = "#0b1014"  # type: ignore[attr-defined]
            dark = True

        else:
            # Unknown theme — fall back to consulting_light
            self.palette = ["#4C72B0", "#C44E52", "#55A868", "#8172B2", "#CCB974"]  # type: ignore[attr-defined]
            self.grid_color = "#DDDDDD"  # type: ignore[attr-defined]
            self.bg_color = "#FFFFFF"  # type: ignore[attr-defined]
            dark = False

        if dark:
            self.color_axes_edge = "#f0f0f0"  # type: ignore[attr-defined]
            self.color_axes_label = "#f0f0f0"  # type: ignore[attr-defined]
            self.color_text_main = "#f0f0f0"  # type: ignore[attr-defined]
            self.color_tick = "#E5E7EB"  # type: ignore[attr-defined]
            self.color_title = "#f0f0f0"  # type: ignore[attr-defined]
            self.color_subtitle = "#999999"  # type: ignore[attr-defined]
            self.color_caption = "#999999"  # type: ignore[attr-defined]
            self.color_spine = "#E5E7EB"  # type: ignore[attr-defined]
        else:
            self.color_axes_edge = "#444444"  # type: ignore[attr-defined]
            self.color_axes_label = "#222222"  # type: ignore[attr-defined]
            self.color_text_main = "#111111"  # type: ignore[attr-defined]
            self.color_tick = "#333333"  # type: ignore[attr-defined]
            self.color_title = "#111111"  # type: ignore[attr-defined]
            self.color_subtitle = "#666666"  # type: ignore[attr-defined]
            self.color_caption = "#555555"  # type: ignore[attr-defined]
            self.color_spine = "#000000"  # type: ignore[attr-defined]

        dpi = getattr(self, "dpi", 150)
        self._rc.update(  # type: ignore[attr-defined]
            {
                "figure.dpi": dpi,
                "font.family": self.font_main_family,
                "axes.titlesize": self._fs(18),
                "axes.labelsize": self._fs(12),
                "xtick.labelsize": self._fs(12),
                "ytick.labelsize": self._fs(12),
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
