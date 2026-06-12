# elegant_chart/bar_mixin.py
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import rc_context

from ._logging import logger
from .data_mixin import DataMixin
from .types import FormatterSpec


class BarMixin(DataMixin):
    def bar(
        self,
        x: Optional[Sequence[Any]] = None,
        ys: Optional[Union[Sequence[Any], Dict[str, Sequence[Any]]]] = None,
        labels: Optional[Sequence[Optional[str]]] = None,
        df: Optional[pd.DataFrame] = None,
        x_col: Optional[str] = None,
        y_cols: Optional[Union[str, Sequence[str]]] = None,
        rotation: float = 0,
        stacked: bool = False,
        bar_width: Optional[float] = None,
        show_value_labels: bool = False,
        compact_years: bool = False,
        x_tick_step: Optional[int] = None,
        max_x_ticks: Optional[int] = None,
        auto_x_thinning: Optional[bool] = None,
        max_label_width: Optional[int] = None,
        label_width_strategy: str = "wrap",
        tick_label_pad: Optional[float] = None,
        # axis controls
        y_tick_step: Optional[float] = None,
        max_y_ticks: Optional[int] = None,
        y_formatter: Optional[FormatterSpec] = None,
        x_formatter: Optional[FormatterSpec] = None,
        xlim: Optional[Tuple[float, float]] = None,
        ylim: Optional[Tuple[float, float]] = None,
        x_minor_ticks: Optional[int] = None,
        x_date_format: Optional[str] = None,
        x_upper_pad: Optional[float] = None,
        align_x_edges: Optional[bool] = None,
        alpha_map: Optional[Dict[str, float]] = None,
        # output
        show: bool = True,
        save_path: Optional[str] = None,
        save_dpi: int = 500,
        save_format: Optional[str] = None,
        export_xlsx: bool = True,
        export_xlsx_path: Optional[str] = None,
        **save_kwargs: Any,
    ) -> Tuple[plt.Figure, plt.Axes]:
        """Create a bar chart with categorical, numeric, or datetime x values."""

        x, series_list, x_plan, active_xlim = self._prepare_render(
            "bar", x, ys, labels, df, x_col, y_cols,
            xlim, x_minor_ticks, x_upper_pad, align_x_edges,
        )
        effective_bar_width = bar_width if bar_width is not None else self._auto_bar_width(x_plan, len(x))

        with rc_context(self._rc):  # type: ignore[attr-defined]
            fig, ax = self._init_figure_and_axes()  # type: ignore[attr-defined]
            self._configure_grid(ax)  # type: ignore[attr-defined]

            base_positions = x_plan.positions
            if self._x_xlim_explicit:  # type: ignore[attr-defined]
                # An explicit xlim defines the range to anchor (spine + boundary
                # ticks); auto upper-padding is skipped for this case.
                self._x_data_bounds = tuple(float(v) for v in active_xlim)  # type: ignore[attr-defined]
            else:
                self._x_data_bounds = (float(base_positions.min()), float(base_positions.max()))  # type: ignore[attr-defined]
            logger.debug("Resolved x data bounds: %s", self._x_data_bounds)  # type: ignore[attr-defined]

            if x_plan.is_datetime:
                ax.xaxis_date()

            # ── draw bars ─────────────────────────────────────────────────
            n_series = len(series_list)
            val_fmt = self._build_formatter(y_formatter if y_formatter is not None else self.y_formatter)  # type: ignore[attr-defined]

            if stacked or n_series == 1:
                cumulative = np.zeros(len(base_positions))
                for idx, (lbl, values) in enumerate(series_list):
                    color = self._series_color(idx, lbl)  # type: ignore[attr-defined]
                    alpha = (alpha_map or {}).get(lbl) if lbl is not None else None
                    ax.bar(
                        base_positions,
                        values,
                        bottom=cumulative if stacked else None,
                        width=effective_bar_width,
                        label=lbl,
                        color=color,
                        alpha=alpha,
                        zorder=2,
                        align="center",
                    )
                    if show_value_labels:
                        for pos, v, cum in zip(base_positions, values, cumulative):
                            bar_top = float(v) + float(cum) if stacked else float(v)
                            ax.text(
                                float(pos), bar_top, val_fmt(float(v), 0),
                                ha="center", va="bottom",
                                fontsize=self._ts("value_label"),  # type: ignore[attr-defined]
                                color=self.color_text_main,  # type: ignore[attr-defined]
                                zorder=6,
                            )
                    if stacked:
                        cumulative += np.array(values, dtype=float)

            else:
                # grouped bars
                single_width = effective_bar_width / n_series
                offset_start = -effective_bar_width / 2 + single_width / 2

                for idx, (lbl, values) in enumerate(series_list):
                    offset = offset_start + idx * single_width
                    color = self._series_color(idx, lbl)  # type: ignore[attr-defined]
                    alpha = (alpha_map or {}).get(lbl) if lbl is not None else None
                    ax.bar(
                        base_positions + offset,
                        values,
                        width=single_width,
                        label=lbl,
                        color=color,
                        alpha=alpha,
                        zorder=2,
                        align="center",
                    )
                    if show_value_labels:
                        for pos, v in zip(base_positions, values):
                            ax.text(
                                float(pos) + offset, float(v), val_fmt(float(v), 0),
                                ha="center", va="bottom",
                                fontsize=self._ts("value_label"),  # type: ignore[attr-defined]
                                color=self.color_text_main,  # type: ignore[attr-defined]
                                zorder=6,
                            )

            # ── axis limits ───────────────────────────────────────────────
            if stacked:
                cumulative_total = np.zeros(len(base_positions))
                for _, values in series_list:
                    cumulative_total += np.asarray(values, dtype=float)
                data_y_max = float(cumulative_total.max())
            else:
                data_y_max = float(
                    max(np.asarray(values, dtype=float).max() for _, values in series_list)
                )
            self._apply_axis_limits(  # type: ignore[attr-defined]
                ax, xlim, ylim, data_y_min=0.0, data_y_max=data_y_max, chart_type="bar"
            )

            # ── x axis ────────────────────────────────────────────────────
            self._dispatch_x_axis(
                ax, x, x_plan,
                rotation=rotation,
                compact_years=compact_years,
                x_tick_step=x_tick_step,
                max_x_ticks=max_x_ticks,
                auto_x_thinning=auto_x_thinning,
                max_label_width=max_label_width,
                label_width_strategy=label_width_strategy,
                tick_label_pad=tick_label_pad,
                x_formatter=x_formatter,
                x_date_format=x_date_format,
            )

            # ── y axis ────────────────────────────────────────────────────
            self._apply_y_axis(  # type: ignore[attr-defined]
                ax,
                y_tick_step=y_tick_step,
                max_y_ticks=max_y_ticks,
                y_formatter=y_formatter,
            )
            ax.tick_params(axis="y", which="both", length=0, pad=0)
            ax.tick_params(axis="x", which="major", direction="out", pad=self._px(3), length=self._px(5), width=self._px(0.5))
            ax.margins(x=0)
            if not self._x_xlim_explicit:  # type: ignore[attr-defined]
                _xlo, _xhi = self._x_data_bounds  # type: ignore[attr-defined]
                if _xlo == _xhi:
                    _xlo -= 0.5
                    _xhi += 0.5
                    self._x_data_bounds = (_xlo, _xhi)  # type: ignore[attr-defined]
                ax.set_xlim(_xlo, _xhi)

            # ── finalize + output ─────────────────────────────────────────
            has_legend = self._should_show_legend(series_list)
            self._finalize_and_output(
                fig, ax,
                rotation=rotation,
                has_legend=has_legend,
                save_path=save_path,
                save_dpi=save_dpi,
                save_format=save_format,
                show=show,
                export_xlsx=export_xlsx,
                export_xlsx_path=export_xlsx_path,
                **save_kwargs,
            )

            return fig, ax
