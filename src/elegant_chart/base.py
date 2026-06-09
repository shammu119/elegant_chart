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
    figsize    — (float, float)
    theme      — str
    font_scale — float
    dpi        — int
    _figure_scale — float  (auto; = min(fw/ref_w, fh/ref_h) against REFERENCE_FIGSIZE)

Axis / tick
    x_tick_step, y_tick_step     — float | None
    max_x_ticks, max_y_ticks     — int | None
    auto_x_thinning              — bool
    y_formatter                  — FormatterSpec
    xlim, ylim                   — (float, float) | None

Logo / footer
    logo_path, logo_height_rel, logo_margin_rel

Internal (set once by _apply_base_style)
    _rc                          — dict[str, Any]   (matplotlib rcParams overlay)
    palette                      — list[str]
    grid_color, bg_color         — str
    color_*                      — str
    font_*                       — str

Norm-max formatter scratch
    _max_y_value                 — float | None
    _norm_max_decimals           — int

Last-render cache (written by bar/line, read by export_data)
    _last_x                      — list | None
    _last_series_list            — list[tuple[str|None, list[float]]] | None
"""

from __future__ import annotations

from typing import Optional, Tuple

from .types import FormatterSpec

# The design reference size (inches).  At this figsize _figure_scale == 1.0.
# Pixel output: REFERENCE_FIGSIZE × default save_dpi = (2.16, 2.7) × 500 = 1080×1350 px.
REFERENCE_FIGSIZE: Tuple[float, float] = (2.16, 2.7)


class ChartBase:
    """Defines and initialises every attribute consumed by the mixins."""

    def __init__(
        self,
        title: Optional[str] = None,
        subtitle: Optional[str] = None,
        xlabel: Optional[str] = None,
        ylabel: Optional[str] = None,
        caption: Optional[str] = None,
        figsize: Tuple[float, float] = REFERENCE_FIGSIZE,
        theme: str = "consulting_light",
        font_scale: float = 0.8,
        dpi: int = 150,
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
        # ── presentation ──────────────────────────────────────────────────
        self.title = title
        self.subtitle = subtitle
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.caption = caption
        self.figsize = figsize
        # Proportional scale relative to the reference design size.
        # 1.0 at the default figsize; grows / shrinks linearly with figure size.
        _ref_w, _ref_h = REFERENCE_FIGSIZE
        _fw, _fh = self.figsize
        self._figure_scale: float = min(_fw / _ref_w, _fh / _ref_h)
        self.theme = theme
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

        # ── logo / footer ──────────────────────────────────────────────────
        self.logo_path = logo_path
        self.logo_height_rel = logo_height_rel
        self.logo_margin_rel = logo_margin_rel

        # ── internal / scratch ────────────────────────────────────────────
        self._max_y_value: Optional[float] = None
        self._norm_max_decimals: int = 0
        self._rc: dict = {}

        # ── last-render cache (populated by bar/line, read by export_data) ─
        self._last_x: Optional[list] = None
        self._last_series_list: Optional[list] = None

        # Populate palette, colors, fonts, and rc overlay
        self._apply_base_style()  # type: ignore[attr-defined]  # provided by StyleMixin
