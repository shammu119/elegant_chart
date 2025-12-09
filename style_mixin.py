# elegant_chart/style_mixin.py
import os
from matplotlib import font_manager


class StyleMixin:
    def _fs(self, base: float) -> float:
        return base * self.font_scale

    def _register_fonts(self) -> None:
        try:
            font_manager.fontManager.addfont("fonts/SF-Pro.ttf")
            font_manager.fontManager.addfont("fonts/SF-Pro-Display-Light.otf")
            font_manager.fontManager.addfont("fonts/SF-Pro-Display-Medium.otf")
            font_manager.fontManager.addfont("fonts/SF-Pro-Text-Bold.otf")
        except OSError:
            pass

    def _configure_fonts(self) -> None:
        self.font_main_family = "SF Pro"

        self.font_title_family = "SF Pro Text"
        self.font_title_weight = "bold"

        self.font_caption_family = "SF Pro Display"
        self.font_caption_weight = "light"

    def _apply_base_style(self) -> None:
        self._register_fonts()
        self._configure_fonts()

        theme = self.theme

        if theme == "consulting_light":
            self.palette = [
                "#4C72B0",
                "#C44E52",
                "#55A868",
                "#8172B2",
                "#CCB974",
            ]
            self.grid_color = "#DDDDDD"
            self.bg_color = "#FFFFFF"
            dark = False

        elif theme == "newsroom_muted":
            self.palette = [
                "#3B5C92",
                "#8C4A5A",
                "#4E7B63",
                "#9467BD",
                "#B5893F",
            ]
            self.grid_color = "#E0E0E0"
            self.bg_color = "#FAFAFA"
            dark = False

        elif theme == "consulting_dark":
            self.palette = [
                "#8FB3FF",
                "#FF8C99",
                "#7AD8A0",
                "#B4A5FF",
                "#F5D27C",
            ]
            self.grid_color = "#333333"
            self.bg_color = "#111827"
            dark = True

        elif theme == "newsroom_dark":
            self.palette = [("#6FE8FF", "#0097A7")]
            self.grid_color = "#444444"
            self.bg_color = "#0b1014"
            dark = True

        else:
            self.palette = [
                "#4C72B0",
                "#C44E52",
                "#55A868",
                "#8172B2",
                "#CCB974",
            ]
            self.grid_color = "#DDDDDD"
            self.bg_color = "#FFFFFF"
            dark = False

        if dark:
            self.color_axes_edge = "#f0f0f0"
            self.color_axes_label = "#f0f0f0"
            self.color_text_main = "#f0f0f0"
            self.color_tick = "#E5E7EB"
            self.color_title = "#f0f0f0"
            self.color_subtitle = "#999999"
            self.color_caption = "#999999"
            self.color_spine = "#E5E7EB"
        else:
            self.color_axes_edge = "#444444"
            self.color_axes_label = "#222222"
            self.color_text_main = "#111111"
            self.color_tick = "#333333"
            self.color_title = "#111111"
            self.color_subtitle = "#666666"
            self.color_caption = "#555555"
            self.color_spine = "#000000"

        self._rc.update(
            {
                "figure.dpi": 500,
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
