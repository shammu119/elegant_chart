# elegant_chart/bar_mixin.py
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import rc_context

from ._logging import logger
from .axis_utils import calc_y_axis
from .data_mixin import DataMixin
from .figure_mixin import GRID_LINEWIDTH
from .style_mixin import LINESPACING
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
        horizontal: bool = False,
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

        if horizontal:
            return self._render_horizontal_bar(
                x, series_list, x_plan,
                bar_width=bar_width,
                show_value_labels=show_value_labels,
                max_label_width=max_label_width,
                label_width_strategy=label_width_strategy,
                y_formatter=y_formatter,
                ylim=ylim,
                alpha_map=alpha_map,
                show=show,
                save_path=save_path,
                save_dpi=save_dpi,
                save_format=save_format,
                export_xlsx=export_xlsx,
                export_xlsx_path=export_xlsx_path,
                **save_kwargs,
            )

        effective_bar_width = bar_width if bar_width is not None else self._auto_bar_width(x_plan, len(x))
        # Edge bars extend half a bar-width beyond the first/last data
        # position; widen the x-limits (in _apply_x_upper_padding) so they
        # aren't clipped against the axes boundary.
        self._bar_half_width = effective_bar_width / 2.0  # type: ignore[attr-defined]

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
                ax, xlim, ylim, data_y_min=0.0, data_y_max=data_y_max, chart_type="bar",
                has_top_label=show_value_labels,
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

    # ── horizontal bar (ranking-chart) variant ─────────────────────────────

    def _render_horizontal_bar(
        self,
        x: Sequence[Any],
        series_list: list,
        x_plan: Any,
        *,
        bar_width: Optional[float],
        show_value_labels: bool,
        max_label_width: Optional[int],
        label_width_strategy: str,
        y_formatter: Optional[FormatterSpec],
        ylim: Optional[Tuple[float, float]],
        alpha_map: Optional[Dict[str, float]],
        show: bool,
        save_path: Optional[str],
        save_dpi: int,
        save_format: Optional[str],
        export_xlsx: bool,
        export_xlsx_path: Optional[str],
        **save_kwargs: Any,
    ) -> Tuple[plt.Figure, plt.Axes]:
        """Minimal horizontal ranking-bar variant: categories on the y-axis
        (top-to-bottom in input order), values on the x-axis.

        This is a simplified rendering path — it shares the framework's
        theme, typography, and footer, but does not replicate the vertical
        bar's boundary-tick / edge-label-alignment / inside-y-tick polish
        (none of which makes sense once the axes are swapped). ``ylim``
        doubles as the value-axis range, mirroring how it bounds the value
        axis for vertical bars.
        """
        effective_bar_width = bar_width if bar_width is not None else self._auto_bar_width(x_plan, len(x))
        base_positions = x_plan.positions
        n_series = len(series_list)
        val_fmt = self._build_formatter(y_formatter if y_formatter is not None else self.y_formatter)  # type: ignore[attr-defined]

        with rc_context(self._rc):  # type: ignore[attr-defined]
            fig, ax = self._init_figure_and_axes()  # type: ignore[attr-defined]
            ax.grid(False, axis="x")
            ax.grid(False, axis="y")

            single_width = effective_bar_width / n_series
            offset_start = -effective_bar_width / 2 + single_width / 2

            for idx, (lbl, values) in enumerate(series_list):
                offset = offset_start + idx * single_width
                color = self._series_color(idx, lbl)  # type: ignore[attr-defined]
                alpha = (alpha_map or {}).get(lbl) if lbl is not None else None
                ax.barh(
                    base_positions + offset, values,
                    height=single_width,
                    label=lbl, color=color, alpha=alpha, zorder=2, align="center",
                )
                if show_value_labels:
                    for pos, v in zip(base_positions, values):
                        ax.annotate(
                            val_fmt(float(v), 0),
                            xy=(float(v), float(pos) + offset),
                            xytext=(self._px(3), 0),  # type: ignore[attr-defined]
                            textcoords="offset points",
                            ha="left", va="center",
                            fontsize=self._ts("value_label"),  # type: ignore[attr-defined]
                            color=self.color_text_main,  # type: ignore[attr-defined]
                            zorder=6,
                        )

            data_x_max = float(
                max(np.asarray(values, dtype=float).max() for _, values in series_list)
            )
            if ylim is not None:
                ax.set_xlim(ylim)
            elif self.ylim is not None:  # type: ignore[attr-defined]
                ax.set_xlim(self.ylim)  # type: ignore[attr-defined]
            else:
                result = calc_y_axis(0.0, data_x_max, "bar", has_top_label=show_value_labels)
                ax.set_xlim(result["y_min"], result["y_max"])
                ax.set_xticks(result["ticks"])

            ax.tick_params(axis="x", which="both", length=0, labelbottom=False)

            # ── category axis (y) ────────────────────────────────────────
            category_labels = [
                self._format_tick_label_width(  # type: ignore[attr-defined]
                    str(lbl), max_width=max_label_width, strategy=label_width_strategy
                )
                for lbl in x
            ]
            ax.set_yticks(base_positions)
            ax.set_yticklabels(category_labels, fontsize=self._ts("tick_label"), color=self.color_tick)  # type: ignore[attr-defined]
            ax.tick_params(axis="y", which="both", length=0, pad=self._px(6))  # type: ignore[attr-defined]
            ax.set_ylim(base_positions.max() + 0.5, base_positions.min() - 0.5)  # first item on top

            # ── baseline spine ───────────────────────────────────────────
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.spines["left"].set_visible(True)
            ax.spines["left"].set_color(self.color_spine)  # type: ignore[attr-defined]
            ax.spines["left"].set_linewidth(self._px(GRID_LINEWIDTH + 0.5))  # type: ignore[attr-defined]
            ax.spines["left"].set_position(("data", 0))

            # ── title / subtitle / axis labels ──────────────────────────────
            # Drawn in figure coordinates (not axes-fraction): the left margin
            # is auto-expanded below to fit long category labels, which would
            # otherwise drag axes-anchored title/subtitle text off the right
            # edge of the figure.
            axes_height = 0.7116 - 0.1266
            if self.title:  # type: ignore[attr-defined]
                fig.text(
                    0.04, 0.1266 + 1.234 * axes_height, self.title,  # type: ignore[attr-defined]
                    fontsize=self._ts("title"),  # type: ignore[attr-defined]
                    va="bottom", ha="left", color=self.color_title,  # type: ignore[attr-defined]
                    fontfamily=self.font_title_family, fontweight=self.font_title_weight,  # type: ignore[attr-defined]
                    linespacing=LINESPACING, clip_on=False,
                )
            if self.subtitle:  # type: ignore[attr-defined]
                fig.text(
                    0.04, 0.1266 + 1.220 * axes_height, self.subtitle,  # type: ignore[attr-defined]
                    fontsize=self._ts("subtitle"),  # type: ignore[attr-defined]
                    va="top", ha="left", color=self.color_subtitle,  # type: ignore[attr-defined]
                    fontfamily=self.font_main_family, linespacing=LINESPACING, clip_on=False,  # type: ignore[attr-defined]
                )
            if self.xlabel:  # type: ignore[attr-defined]
                ax.set_xlabel(self.xlabel, color=self.color_axes_label, fontsize=self._ts("axis_label"))  # type: ignore[attr-defined]
            if self.ylabel:  # type: ignore[attr-defined]
                ax.set_ylabel(self.ylabel, color=self.color_axes_label, fontsize=self._ts("axis_label"))  # type: ignore[attr-defined]

            has_legend = self._should_show_legend(series_list)
            if has_legend:
                handles, lbls = ax.get_legend_handles_labels()
                ncol = max(1, min(self.legend_ncol or 3, len(lbls)))  # type: ignore[attr-defined]
                ax.legend(
                    handles, lbls, loc="upper left", bbox_to_anchor=(0.0, 1.15),
                    ncol=ncol, frameon=False, fontsize=self._ts("legend"),  # type: ignore[attr-defined]
                    handlelength=self._px(1.4), handletextpad=self._px(0.4),  # type: ignore[attr-defined]
                    columnspacing=self._px(1.0), labelspacing=0.1, borderaxespad=0.0,  # type: ignore[attr-defined]
                )

            plt.subplots_adjust(left=0.04, right=0.97, top=0.7116, bottom=0.1266)
            self._auto_expand_bottom(ax)  # type: ignore[attr-defined]

            # Drawn at the original 0.04-0.97 figure-fraction frame, before the
            # axes are pushed right/narrowed below, so the footer rule and
            # caption stay aligned with the title's left edge regardless of
            # how wide the category labels are.
            self._add_footer(fig)  # type: ignore[attr-defined]

            self._auto_expand_left(ax)  # type: ignore[attr-defined]
            self._auto_expand_right(ax, ax.get_xticklabels())  # type: ignore[attr-defined]

            if save_path is not None:
                self.save_figure(fig, save_path, dpi=save_dpi, fmt=save_format, **save_kwargs)  # type: ignore[attr-defined]
                logger.info("Saved chart -> %s", save_path)
                if export_xlsx:
                    import os  # noqa: PLC0415
                    target = export_xlsx_path or os.path.join(
                        os.path.dirname(str(save_path)) or ".", "chart_data.xlsx"
                    )
                    try:
                        self.export_data(target)  # type: ignore[attr-defined]
                        logger.info("Exported chart data -> %s", target)
                    except ImportError:
                        logger.warning(
                            "Skipped chart_data.xlsx export: openpyxl is not installed "
                            "(install with `pip install openpyxl`)."
                        )

            if show:
                plt.show()

            return fig, ax
