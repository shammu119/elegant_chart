# elegant_chart/render.py
"""
``render(spec, df)`` — draw a :class:`~elegant_chart.spec.ChartSpec`.

This module only *routes* spec fields onto the library's existing API: each
setting goes to ``ElegantChart(...)`` or to ``bar()/line()/bump()`` exactly as
those methods take it today.  It adds no styling of its own, so a chart drawn
through ``render`` is pixel-identical to the same chart written by hand.

The figure is always built at the canonical ``figsize`` (1080 × 1350 px at
500 DPI).  Previews only change the ``savefig`` DPI, so preview and export
are the same image at different resolutions.
"""

from __future__ import annotations

import io
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Optional

import matplotlib.pyplot as plt
import pandas as pd

from .elegant_chart import ElegantChart
from .spec import CHART_TYPES, ChartSpec

EXPORT_DPI = 500


class SpecError(ValueError):
    """The spec doesn't fit the data (missing column, nothing to plot, …)."""


@dataclass
class RenderResult:
    fig: plt.Figure
    ax: plt.Axes
    chart: ElegantChart

    def close(self) -> None:
        plt.close(self.fig)


# ── column resolution ────────────────────────────────────────────────────────


def resolve_columns(spec: ChartSpec, df: pd.DataFrame) -> tuple[str, list[str]]:
    """Return ``(x_col, y_cols)``, filling sensible defaults when unset.

    Default x = first column; default y = every numeric column except x.
    """
    if df is None or df.empty:
        raise SpecError("There is no data to plot.")
    cols = list(df.columns)
    x_col = spec.chart.x_col if spec.chart.x_col is not None else cols[0]
    if x_col not in df.columns:
        raise SpecError(f"X column '{x_col}' is not in the data.")
    y_cols = [c for c in spec.chart.y_cols]
    if not y_cols:
        y_cols = [c for c in df.select_dtypes("number").columns if c != x_col]
    missing = [c for c in y_cols if c not in df.columns]
    if missing:
        raise SpecError(f"Series column(s) not in the data: {', '.join(map(str, missing))}.")
    if not y_cols:
        raise SpecError("Choose at least one numeric series column.")
    non_numeric = [c for c in y_cols if not pd.api.types.is_numeric_dtype(df[c])]
    if non_numeric:
        raise SpecError(f"Series column(s) must be numeric: {', '.join(map(str, non_numeric))}.")
    return x_col, y_cols


# ── kwargs builders ──────────────────────────────────────────────────────────


def y_formatter_value(spec: ChartSpec) -> Any:
    a = spec.style.axes
    if a.y_formatter == "norm_max":
        return ("norm_max", int(a.y_formatter_decimals))
    if a.y_formatter == "custom":
        return a.y_formatter_custom or "compact"
    return a.y_formatter


def logo_path_value(spec: ChartSpec) -> Optional[str]:
    lay = spec.style.layout
    if lay.logo_mode == "none":
        return ""
    if lay.logo_mode == "custom" and lay.logo_path:
        return lay.logo_path
    return None  # bundled logo


def build_chart_kwargs(spec: ChartSpec) -> dict[str, Any]:
    """Keyword arguments for ``ElegantChart(...)``."""
    t, lay, a, c = spec.style.text, spec.style.layout, spec.style.axes, spec.style.colors
    return dict(
        title=t.title or None,
        subtitle=t.subtitle or None,
        caption=t.caption or None,
        xlabel=t.xlabel or None,
        ylabel=t.ylabel or None,
        annotations=[dict(x) for x in t.annotations] or None,
        theme=c.theme,
        color_map=dict(c.color_map) or None,
        x_tick_step=a.x_tick_step,
        max_x_ticks=a.max_x_ticks,
        auto_x_thinning=a.auto_x_thinning,
        y_tick_step=a.y_tick_step,
        max_y_ticks=a.max_y_ticks,
        y_formatter=y_formatter_value(spec),
        xlim=a.xlim,
        ylim=a.ylim,
        x_minor_ticks=a.x_minor_ticks,
        x_date_format=a.x_date_format or None,
        x_upper_pad=lay.x_upper_pad,
        legend_ncol=spec.style.legend.legend_ncol,
        align_x_edges=lay.align_x_edges,
        logo_path=logo_path_value(spec),
        show_footer=lay.show_footer,
        y_axis_side=lay.y_axis_side,
        y_tick_labels_inside=lay.y_tick_labels_inside,
        show_y_axis=lay.show_y_axis,
        show_y_spine=lay.show_y_spine,
    )


def build_call_kwargs(spec: ChartSpec, df: pd.DataFrame) -> tuple[str, dict[str, Any]]:
    """Return ``(method_name, kwargs)`` for the ``bar()/line()/bump()`` call."""
    ctype = spec.chart.type
    if ctype not in CHART_TYPES:
        raise SpecError(f"Unknown chart type '{ctype}'.")
    x_col, y_cols = resolve_columns(spec, df)
    ch, lay, a = spec.chart, spec.style.layout, spec.style.axes
    output = dict(show=False, save_path=None, export_xlsx=False)

    if ctype == "bump":
        ys = {
            str(c): [None if pd.isna(v) else float(v) for v in df[c].tolist()] for c in y_cols
        }
        return "bump", dict(
            x=df[x_col].tolist(),
            ys=ys,
            ascending=ch.ascending,
            highlight=list(ch.highlight) or None,
            label_logos=dict(ch.logos) or None,
            **output,
        )

    alpha_map = {k: float(v) for k, v in spec.style.colors.alpha_map.items() if v is not None}
    common = dict(
        df=df,
        x_col=x_col,
        y_cols=list(y_cols),
        rotation=ch.rotation,
        show_value_labels=ch.show_value_labels,
        compact_years=ch.compact_years,
        x_tick_step=a.x_tick_step,
        max_x_ticks=a.max_x_ticks,
        auto_x_thinning=a.auto_x_thinning,
        max_label_width=lay.max_label_width,
        label_width_strategy=lay.label_width_strategy,
        tick_label_pad=lay.tick_label_pad,
        y_tick_step=a.y_tick_step,
        max_y_ticks=a.max_y_ticks,
        y_formatter=y_formatter_value(spec),
        xlim=a.xlim,
        ylim=a.ylim,
        x_minor_ticks=a.x_minor_ticks,
        x_date_format=a.x_date_format or None,
        x_upper_pad=lay.x_upper_pad,
        align_x_edges=lay.align_x_edges,
        alpha_map=alpha_map or None,
        **output,
    )
    if ctype in ("bar", "hbar"):
        return "bar", dict(
            common,
            stacked=ch.stacked,
            horizontal=ctype == "hbar",
            bar_width=ch.bar_width,
            y_tick_logos=(dict(ch.logos) or None) if ctype == "hbar" else None,
        )
    return "line", dict(
        common,
        markers=ch.markers,
        linewidth=ch.linewidth,
        x_year_tick_interval=a.x_year_tick_interval,
    )


# ── render / output ──────────────────────────────────────────────────────────


def render(spec: ChartSpec, df: pd.DataFrame) -> RenderResult:
    """Draw ``spec`` with ``df`` and return the live figure (caller closes it)."""
    method, call_kwargs = build_call_kwargs(spec, df)
    chart = ElegantChart(**build_chart_kwargs(spec))
    before = set(plt.get_fignums())
    try:
        fig, ax = getattr(chart, method)(**call_kwargs)
    except Exception:
        for num in set(plt.get_fignums()) - before:
            plt.close(num)
        raise
    return RenderResult(fig=fig, ax=ax, chart=chart)


def figure_png_bytes(fig: plt.Figure, dpi: int = EXPORT_DPI) -> bytes:
    """PNG bytes of ``fig`` at ``dpi`` (500 → 1080 × 1350 px at default figsize)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi)
    return buf.getvalue()


def chart_data_xlsx_bytes(chart: ElegantChart) -> bytes:
    """``chart_data.xlsx`` bytes for the data actually plotted (via ``export_data``)."""
    fd, path = tempfile.mkstemp(suffix=".xlsx")
    os.close(fd)
    try:
        chart.export_data(path)
        with open(path, "rb") as fh:
            return fh.read()
    finally:
        os.remove(path)

