# elegant_chart/base.py
"""
ChartBase — the single source of truth for the shared attribute contract.

Every mixin in this library reads from ``self.*`` without defining those
attributes.  ``ChartBase.__init__`` is the only place they are created, making
the contract explicit and type-checkable rather than implicit convention.

Attribute contract (mixins may read, only __init__ writes)
----------------------------------------------------------
Presentation
    title, subtitle, xlabel, ylabel, caption  — str | None
    annotations — list[dict] (sparse muted-grey in-plot callouts; see FigureMixin._draw_annotations)
    figsize    — (float, float)
    theme      — str
    color_map  — dict[str, str]  (series label -> role name or hex; optional
                  per-series override consumed by StyleMixin._series_color)
    font_scale — float
    dpi        — int
    _figure_scale — float  (auto; = min(fw/ref_w, fh/ref_h) against REFERENCE_FIGSIZE)

Axis / tick
    x_tick_step, y_tick_step     — float | None
    max_x_ticks, max_y_ticks     — int | None
    auto_x_thinning              — bool
    y_formatter                  — FormatterSpec
    xlim, ylim                   — (float, float) | None
    x_minor_ticks                — int | None  (minor ticks per major interval;
                                    1 == a single midpoint tick, e.g. mid-year)
    x_date_format                — str | None  (strftime format, e.g. "%Y", for
                                    datetime x-axes; when set, uses a fixed
                                    DateFormatter and skips endpoint-pinning so the
                                    locator places clean, evenly-spaced ticks. The
                                    true data range remains anchored by the
                                    unlabeled boundary tick marks)
    x_upper_pad                  — float | None  (relative-to-data-span pad added
                                    to the upper xlim; None == auto-measured from
                                    the rendered inside y-tick label widths)
    align_x_edges                — bool  (left-align the first x tick label and
                                    right-align the last, instead of centering)

Logo / footer
    logo_path, logo_height_rel, logo_margin_rel — logo_path=None (default) uses
    the bundled elegant_chart logo (see _paths.DEFAULT_LOGO_PATH); pass a path
    (absolute, ``~``-relative, or relative to the working directory) to use a
    different image, or "" to disable the logo entirely.

Internal (set once by _apply_base_style)
    _rc                          — dict[str, Any]   (matplotlib rcParams overlay)
    palette                      — list[str]
    color_roles                  — dict[str, str]  (role name -> hex, derived
                                    from palette[0..n]; see StyleMixin._series_color)
    grid_color, bg_color         — str
    color_*                      — str
    font_*                       — str

Norm-max formatter scratch
    _max_y_value                 — float | None
    _norm_max_decimals           — int

Last-render cache (written by bar/line, read by export_data)
    _last_x                      — list | None
    _last_series_list            — list[tuple[str|None, list[float]]] | None

Last-render x-axis state (written by bar/line, read by AxisMixin/FigureMixin
during _finalize_axes)
    _x_data_bounds               — (float, float) | None  (numeric position
                                    min/max of the actual data, pre-padding)
    _x_minor_ticks               — int | None
    _x_upper_pad                 — float | None
    _align_x_edges                — bool
"""

from __future__ import annotations

from typing import Any, Optional, Tuple

from .types import FormatterSpec

# Design reference size (inches) — _figure_scale == 1.0 here; all font/geometry specs are
# authored at this canvas size and scale proportionally when figsize differs.
REFERENCE_FIGSIZE: Tuple[float, float] = (3.6, 4.5)


class ChartBase:
    """Defines and initialises every attribute consumed by the mixins."""

    def __init__(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        xlabel: Optional[str] = None,
        ylabel: Optional[str] = None,
        caption: Optional[str] = None,
        figsize: Tuple[float, float] = (2.16, 2.70),  # 1080×1350 px at 500 DPI
        theme: str = "newsroom_dark",
        color_map: Optional[dict[str, str]] = None,
        font_scale: float = 0.9,
        dpi: int = 500,
        x_tick_step: Optional[float] = None,
        max_x_ticks: Optional[int] = None,
        auto_x_thinning: bool = True,
        y_tick_step: Optional[float] = None,
        max_y_ticks: Optional[int] = None,
        y_formatter: FormatterSpec = "compact",
        xlim: Optional[Tuple[float, float]] = None,
        ylim: Optional[Tuple[float, float]] = None,
        x_minor_ticks: Optional[int] = None,
        x_date_format: Optional[str] = None,
        x_upper_pad: Optional[float] = None,
        align_x_edges: bool = True,
        logo_path: Optional[str] = None,
        logo_height_rel: float = 0.12,
        logo_margin_rel: float = 0.02,
        show_footer: bool = True,
        y_axis_side: str = "right",
        y_tick_labels_inside: bool = True,
        show_y_spine: bool = False,
        annotations: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        # ── presentation ──────────────────────────────────────────────────
        self.title = title
        self.subtitle = subtitle
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.caption = caption
        self.annotations = annotations or []
        self.figsize = figsize
        # Proportional scale relative to the reference design size.
        # 1.0 at the default figsize; grows / shrinks linearly with figure size.
        _ref_w, _ref_h = REFERENCE_FIGSIZE
        _fw, _fh = self.figsize
        self._figure_scale: float = min(_fw / _ref_w, _fh / _ref_h)
        self.theme = theme
        self.color_map = color_map or {}
        self.font_scale = font_scale
        self.dpi = dpi

        # ── axis / tick ────────────────────────────────────────────────────
        self.x_tick_step = x_tick_step
        self.max_x_ticks = max_x_ticks
        self.auto_x_thinning = auto_x_thinning

        self.y_tick_step = y_tick_step
        self.max_y_ticks = max_y_ticks
        self.y_formatter = y_formatter

        self.xlim = xlim
        self.ylim = ylim

        self.x_minor_ticks = x_minor_ticks
        self.x_date_format = x_date_format
        self.x_upper_pad = x_upper_pad
        self.align_x_edges = align_x_edges

        # ── logo / footer ──────────────────────────────────────────────────
        self.logo_path = logo_path
        self.logo_height_rel = logo_height_rel
        self.logo_margin_rel = logo_margin_rel
        self.show_footer = show_footer
        self.y_axis_side = y_axis_side
        self.y_tick_labels_inside = y_tick_labels_inside
        self.show_y_spine = show_y_spine

        # ── internal / scratch ────────────────────────────────────────────
        self._max_y_value: Optional[float] = None
        self._norm_max_decimals: int = 0
        self._rc: dict = {}

        # ── last-render cache (populated by bar/line, read by export_data) ─
        self._last_x: Optional[list] = None
        self._last_series_list: Optional[list] = None

        # ── last-render x-axis state (populated by bar/line, read by
        # AxisMixin/FigureMixin during _finalize_axes) ─────────────────────
        self._x_data_bounds: Optional[Tuple[float, float]] = None
        self._x_minor_ticks: Optional[int] = self.x_minor_ticks
        self._x_upper_pad: Optional[float] = self.x_upper_pad
        self._align_x_edges: bool = self.align_x_edges
        self._x_xlim_explicit: bool = False

        # Populate palette, colors, fonts, and rc overlay
        self._apply_base_style()  # type: ignore[attr-defined]  # provided by StyleMixin
