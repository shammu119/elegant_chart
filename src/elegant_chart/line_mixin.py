# elegant_chart/line_mixin.py
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import rc_context

from ._logging import logger
from .data_mixin import DataMixin
from .types import FormatterSpec


class LineMixin(DataMixin):
    def line(
        self,
        x: Optional[Sequence[Any]] = None,
        ys: Optional[Union[Sequence[Any], Dict[str, Sequence[Any]]]] = None,
        labels: Optional[Sequence[Optional[str]]] = None,
        df: Optional[pd.DataFrame] = None,
        x_col: Optional[str] = None,
        y_cols: Optional[Union[str, Sequence[str]]] = None,
        rotation: float = 0,
        markers: bool = False,
        linewidth: Optional[float] = None,
        show_value_labels: bool = False,
        compact_years: bool = False,
        x_tick_step: Optional[int] = None,
        max_x_ticks: Optional[int] = None,
        auto_x_thinning: Optional[bool] = None,
        max_label_width: Optional[int] = None,
        label_width_strategy: str = "wrap",
        tick_label_pad: Optional[float] = None,
        y_tick_step: Optional[float] = None,
        max_y_ticks: Optional[int] = None,
        y_formatter: Optional[FormatterSpec] = None,
        x_formatter: Optional[FormatterSpec] = None,
        xlim: Optional[Tuple[float, float]] = None,
        ylim: Optional[Tuple[float, float]] = None,
        x_minor_ticks: Optional[int] = None,
        x_date_format: Optional[str] = None,
        x_year_tick_interval: Optional[int] = None,
        x_upper_pad: Optional[float] = None,
        align_x_edges: Optional[bool] = None,
        alpha_map: Optional[Dict[str, float]] = None,
        show: bool = True,
        save_path: Optional[str] = None,
        save_dpi: int = 500,
        save_format: Optional[str] = None,
        export_xlsx: bool = True,
        export_xlsx_path: Optional[str] = None,
        **save_kwargs: Any,
    ) -> Tuple[plt.Figure, plt.Axes]:
        """Create a line chart with categorical, numeric, or datetime x values."""

        x, series_list, x_plan, active_xlim = self._prepare_render(
            "line", x, ys, labels, df, x_col, y_cols,
            xlim, x_minor_ticks, x_upper_pad, align_x_edges,
        )

        # Resolve linewidth: None → auto-scale from reference; explicit float → honour as-is.
        effective_lw = linewidth if linewidth is not None else self._px(0.6)  # type: ignore[attr-defined]

        with rc_context(self._rc):  # type: ignore[attr-defined]
            fig, ax = self._init_figure_and_axes()  # type: ignore[attr-defined]
            self._configure_grid(ax)  # type: ignore[attr-defined]

            x_positions = x_plan.positions
            if self._x_xlim_explicit:  # type: ignore[attr-defined]
                # An explicit xlim defines the range to anchor (spine + boundary
                # ticks); auto upper-padding is skipped for this case.
                self._x_data_bounds = tuple(float(v) for v in active_xlim)  # type: ignore[attr-defined]
            else:
                self._x_data_bounds = (float(x_positions.min()), float(x_positions.max()))  # type: ignore[attr-defined]
            logger.debug("Resolved x data bounds: %s", self._x_data_bounds)  # type: ignore[attr-defined]

            if x_plan.is_datetime:
                ax.xaxis_date()

            # ── draw lines ────────────────────────────────────────────────
            val_fmt = self._build_formatter(
                y_formatter if y_formatter is not None else self.y_formatter
            )  # type: ignore[attr-defined]

            for idx, (lbl, values) in enumerate(series_list):
                color = self._series_color(idx, lbl)  # type: ignore[attr-defined]
                alpha = (alpha_map or {}).get(lbl) if lbl is not None else None
                if markers:
                    ax.plot(
                        x_positions,
                        values,
                        label=lbl,
                        color=color,
                        alpha=alpha,
                        linewidth=effective_lw,
                        marker="o",
                        markersize=self._px(2),  # type: ignore[attr-defined]
                        zorder=2,
                    )
                else:
                    ax.plot(
                        x_positions,
                        values,
                        label=lbl,
                        color=color,
                        alpha=alpha,
                        linewidth=effective_lw,
                        zorder=2,
                    )

                if show_value_labels:
                    for xp, v in zip(x_positions, values):
                        ax.annotate(
                            val_fmt(float(v), 0),
                            xy=(float(xp), float(v)),
                            xytext=(0, self._px(5)),  # type: ignore[attr-defined]
                            textcoords="offset points",
                            ha="center",
                            va="bottom",
                            fontsize=self._ts("value_label"),  # type: ignore[attr-defined]
                            color=self.color_text_main,  # type: ignore[attr-defined]
                            zorder=6,
                        )

            # ── axis limits ───────────────────────────────────────────────
            all_values = [v for _, values in series_list for v in values]
            data_y_min = float(min(all_values))
            data_y_max = float(max(all_values))
            self._apply_axis_limits(  # type: ignore[attr-defined]
                ax, xlim, ylim, data_y_min=data_y_min, data_y_max=data_y_max, chart_type="line",
                has_top_label=show_value_labels,
            )
            self._apply_y_axis(  # type: ignore[attr-defined]
                ax,
                y_tick_step=y_tick_step,
                max_y_ticks=max_y_ticks,
                y_formatter=y_formatter,
            )

            ax.tick_params(axis="y", which="both", length=0, pad=0)
            ax.tick_params(
                axis="x", which="major", direction="out", pad=self._px(3), length=self._px(5), width=self._px(0.5)
            )
            ax.margins(x=0)

            if active_xlim is None and not x_plan.is_datetime:
                ax.set_xlim(float(x_positions.min()), float(x_positions.max()))

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
                x_year_tick_interval=x_year_tick_interval,
            )

            # ── finalize + output ─────────────────────────────────────────
            has_legend = self._should_show_legend(series_list)
            self._finalize_and_output(
                fig,
                ax,
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
