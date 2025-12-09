# elegant_chart/elegant_chart.py
from typing import Optional, Tuple, Any
from .types import FormatterSpec, YFormatter
from .style_mixin import StyleMixin
from .axis_mixin import AxisMixin
from .gradient_mixin import GradientMixin
from .figure_mixin import FigureMixin
from .line_mixin import LineMixin
from .bar_mixin import BarMixin


class ElegantChart(
    StyleMixin,
    AxisMixin,
    GradientMixin,
    FigureMixin,
    LineMixin,
    BarMixin,
):
    def __init__(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        xlabel: Optional[str] = None,
        ylabel: Optional[str] = None,
        caption: Optional[str] = None,
        figsize: Tuple[float, float] = (9, 6),
        theme: str = "consulting_light",
        font_scale: float = 1.0,
        x_tick_step: Optional[float] = None,
        max_x_ticks: Optional[int] = None,
        auto_x_thinning: bool = True,
        y_tick_step: Optional[float] = None,
        max_y_ticks: Optional[int] = None,
        y_formatter: FormatterSpec = "compact",
        xlim: Optional[Tuple[float, float]] = None,
        ylim: Optional[Tuple[float, float]] = None,
        logo_path: Optional[str] = "~/logo/ce_logo.png",
        logo_height_rel: float = 0.12,
        logo_margin_rel: float = 0.02,
    ) -> None:
        self.title = title
        self.subtitle = subtitle
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.caption = caption
        self.figsize = figsize
        self.theme = theme
        self.font_scale = font_scale

        self.x_tick_step = x_tick_step
        self.max_x_ticks = max_x_ticks
        self.auto_x_thinning = auto_x_thinning

        self.y_tick_step = y_tick_step
        self.max_y_ticks = max_y_ticks
        self.y_formatter = y_formatter

        self.xlim = xlim
        self.ylim = ylim

        self.logo_path = logo_path
        self.logo_height_rel = logo_height_rel
        self.logo_margin_rel = logo_margin_rel

        self._max_y_value: Optional[float] = None
        self._norm_max_decimals: int = 0

        self._rc = {}
        self._apply_base_style()
