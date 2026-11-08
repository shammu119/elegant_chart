# elegant_chart/spec.py
"""
ChartSpec — one plain, serialisable description of a chart.

A ``ChartSpec`` holds everything needed to go from raw data to a finished
chart: where the data comes from, the reshape steps, the chart type and its
columns, and every style setting.  It deliberately mirrors the parameters the
library already accepts; :func:`elegant_chart.render.render` routes each field
to ``ElegantChart(...)`` or to ``bar()/line()/bump()`` as the library expects.

Switching chart type only changes ``spec.chart.type`` — data, reshaping and
all shared style settings are kept.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Optional, Tuple

CHART_TYPES: Tuple[str, ...] = ("bar", "hbar", "line", "bump")
CHART_TYPE_LABELS = {
    "bar": "Bar",
    "hbar": "Horizontal bar",
    "line": "Line",
    "bump": "Bump (ranking)",
}
STEP_OPS: Tuple[str, ...] = ("filter", "group", "sort", "top_n", "pivot")
FILTER_OPERATORS: Tuple[str, ...] = ("=", "≠", ">", "≥", "<", "≤", "in")
AGGREGATIONS: Tuple[str, ...] = ("sum", "mean", "count", "min", "max")
THEMES: Tuple[str, ...] = ("newsroom_dark", "newsroom_muted", "consulting_light", "consulting_dark")
COLOR_ROLES: Tuple[str, ...] = ("primary", "secondary", "tertiary", "quaternary", "quinary")
Y_FORMATTERS: Tuple[str, ...] = ("compact", "plain", "percent", "norm_max", "custom")
LABEL_WIDTH_STRATEGIES: Tuple[str, ...] = ("wrap", "truncate")
LOGO_MODES: Tuple[str, ...] = ("default", "none", "custom")


@dataclass
class SourceSpec:
    """Where the raw data comes from."""

    kind: str = "none"  # "mma" | "file" | "none"
    series_id: Optional[int] = None
    name: Optional[str] = None  # uploaded file name
    sheet: Optional[str] = None  # Excel sheet name


@dataclass
class StepSpec:
    """One reshape step: ``op`` is one of :data:`STEP_OPS`."""

    op: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class ChartTypeSpec:
    """Chart type, columns, and type-specific options."""

    type: str = "bar"
    x_col: Optional[str] = None
    y_cols: list[str] = field(default_factory=list)
    # shared bar/line
    show_value_labels: bool = False
    rotation: float = 0.0
    compact_years: bool = False
    # bar / hbar
    stacked: bool = False
    bar_width: Optional[float] = None
    # line
    markers: bool = False
    linewidth: Optional[float] = None
    # bump
    highlight: list[str] = field(default_factory=list)  # empty == every series is a hero
    ascending: bool = False
    hero_linewidth: Optional[float] = None  # None == library default (2.5pt, scaled)
    other_linewidth: Optional[float] = None  # None == library default (1pt, scaled)
    other_color: str = "#BBBBBB"  # non-highlighted ("ghost") lines
    other_alpha: float = 0.6
    label_display: dict[str, str] = field(default_factory=dict)  # series -> shown label text
    # hbar (y_tick_logos) and bump (label_logos): {label: image path}
    logos: dict[str, str] = field(default_factory=dict)


@dataclass
class TextSpec:
    title: Optional[str] = None
    subtitle: Optional[str] = None
    caption: Optional[str] = None
    xlabel: Optional[str] = None
    ylabel: Optional[str] = None
    # each: {x, y, text, dx, dy, arrow, ha, va} — see FigureMixin._draw_annotations
    annotations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LayoutSpec:
    x_upper_pad: Optional[float] = None
    align_x_edges: bool = True
    tick_label_pad: Optional[float] = None
    max_label_width: Optional[int] = None
    label_width_strategy: str = "wrap"
    logo_mode: str = "default"  # "default" (bundled) | "none" | "custom"
    logo_path: Optional[str] = None  # used when logo_mode == "custom"
    show_footer: bool = True
    y_axis_side: str = "right"
    y_tick_labels_inside: bool = True
    show_y_axis: bool = True
    show_y_spine: bool = False


@dataclass
class AxesSpec:
    x_tick_step: Optional[float] = None
    max_x_ticks: Optional[int] = None
    auto_x_thinning: bool = True
    y_tick_step: Optional[float] = None
    max_y_ticks: Optional[int] = None
    x_date_format: Optional[str] = None
    x_minor_ticks: Optional[int] = None
    x_year_tick_interval: Optional[int] = None
    xlim: Optional[Tuple[float, float]] = None
    ylim: Optional[Tuple[float, float]] = None
    y_formatter: str = "compact"  # one of Y_FORMATTERS
    y_formatter_decimals: int = 0  # for "norm_max"
    y_formatter_custom: str = "{x:,.0f}"  # for "custom"


@dataclass
class ColorsSpec:
    theme: str = "newsroom_dark"
    color_map: dict[str, str] = field(default_factory=dict)  # label -> role or hex
    alpha_map: dict[str, float] = field(default_factory=dict)  # label -> 0..1


@dataclass
class LegendSpec:
    legend_ncol: Optional[int] = None


@dataclass
class StyleSpec:
    text: TextSpec = field(default_factory=TextSpec)
    layout: LayoutSpec = field(default_factory=LayoutSpec)
    axes: AxesSpec = field(default_factory=AxesSpec)
    colors: ColorsSpec = field(default_factory=ColorsSpec)
    legend: LegendSpec = field(default_factory=LegendSpec)


@dataclass
class ChartSpec:
    """Everything needed to draw one chart.  See module docstring."""

    source: SourceSpec = field(default_factory=SourceSpec)
    steps: list[StepSpec] = field(default_factory=list)
    chart: ChartTypeSpec = field(default_factory=ChartTypeSpec)
    style: StyleSpec = field(default_factory=StyleSpec)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChartSpec":
        data = data or {}
        style = data.get("style") or {}
        return cls(
            source=_build(SourceSpec, data.get("source")),
            steps=[_build(StepSpec, s) for s in data.get("steps") or []],
            chart=_build(ChartTypeSpec, data.get("chart")),
            style=StyleSpec(
                text=_build(TextSpec, style.get("text")),
                layout=_build(LayoutSpec, style.get("layout")),
                axes=_build(AxesSpec, style.get("axes")),
                colors=_build(ColorsSpec, style.get("colors")),
                legend=_build(LegendSpec, style.get("legend")),
            ),
        )


_TUPLE_FIELDS = {"xlim", "ylim"}


def _build(cls: type, data: Optional[dict[str, Any]]) -> Any:
    """Construct dataclass ``cls`` from ``data``, ignoring unknown keys."""
    data = data or {}
    names = {f.name for f in fields(cls)}
    kwargs = {}
    for key, value in data.items():
        if key not in names:
            continue
        if key in _TUPLE_FIELDS and value is not None:
            value = tuple(value)
        kwargs[key] = value
    return cls(**kwargs)
