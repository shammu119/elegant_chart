# elegant_chart/bar_mixin.py
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rc_context

from .types import FormatterSpec
from .data_mixin import DataMixin


class BarMixin(DataMixin):
    def bar(
        self,
        x: Sequence[Any],
        ys: Optional[Union[Sequence[Any], Dict[str, Sequence[Any]]]] = None,
        labels: Optional[Sequence[Optional[str]]] = None,
        df: Optional[pd.DataFrame] = None,
        x_col: Optional[str] = None,
        y_cols: Optional[Union[str, Sequence[str]]] = None,
        rotation: float = 0,
        stacked: bool = False,
        bar_width: float = 0.7,
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
        # behavior
        show: bool = True,
        save_path: Optional[str] = None,
        save_dpi: int = 500,
        save_format: Optional[str] = None,
        **save_kwargs: Any,
    ) -> Tuple[plt.Figure, plt.Axes]:
        """
        Create a bar chart with categorical, numeric, or datetime x values.
        """
        # dataframe shortcut
        if df is not None:
            if x_col is None or y_cols is None:
                raise ValueError("If df is provided, x_col and y_cols must be set")
            x, ys, labels = self._from_dataframe(df, x_col, y_cols)

        if ys is None:
            raise ValueError("ys must be provided (or use df + x_col + y_cols)")

        # normalize/validate data
        series_list = self._normalize_series(ys, labels)
        self._validate_series_lengths(x, series_list)
        self._validate_values(series_list)
        self._compute_max_y_value(series_list)

        with rc_context(self._rc):
            fig, ax = self._init_figure_and_axes()
            self._configure_grid(ax)

            # ----------------------------
            # x typing and base positions
            # ----------------------------
            first_x = x[0]
            is_categorical = isinstance(first_x, str)
            is_datetime = self._is_datetime_like(first_x)
            is_numeric = not is_categorical and not is_datetime

            numeric_like_labels = False
            numeric_label_values = None
            use_numeric_axis_with_labels = False
            x_tick_labels_forced = None

            active_xlim = xlim if xlim is not None else self.xlim

            if is_categorical:
                # detect numeric-like labels so they can obey numeric xlim
                try:
                    numeric_label_values = np.array([float(v) for v in x], dtype=float)
                    numeric_like_labels = True
                except Exception:
                    numeric_like_labels = False

                if numeric_like_labels and active_xlim is not None:
                    # treat as numeric axis
                    is_categorical = False
                    is_numeric = True
                    use_numeric_axis_with_labels = True
                    x_tick_labels_forced = list(x)
                    base_positions = numeric_label_values
                else:
                    base_positions = np.arange(len(x), dtype=float)

            elif is_datetime:
                base_positions = mdates.date2num(x)
                ax.xaxis_date()

            else:
                base_positions = np.asarray(x, dtype=float)

            # ----------------------------
            # draw bars
            # ----------------------------
            n_series = len(series_list)

            if stacked or n_series == 1:
                cumulative = np.zeros(len(base_positions))
                for idx, (lbl, values) in enumerate(series_list):
                    if self.theme == "newsroom_dark":
                        top_color = "#64D2FF"
                        bottom_color = "#0077CC"

                        heights = np.array(values, dtype=float)
                        bottoms = cumulative if stacked else np.zeros_like(heights)

                        # draw gradient bar per category
                        for xi, h, btm in zip(base_positions, heights, bottoms):
                            if h == 0:
                                continue

                            # invisible base bar just to reserve space
                            ax.bar(
                                xi,
                                h,
                                bottom=btm,
                                width=bar_width,
                                color="none",
                                edgecolor="none",
                                zorder=1,
                                align="center",
                            )

                            # gradient fill
                            self._make_vertical_gradient(
                                ax,
                                x0=xi - bar_width / 2.0,
                                y0=btm,
                                width=bar_width,
                                height=h,
                                top_color=top_color,
                                bottom_color=bottom_color,
                                z=2,
                            )

                        if stacked:
                            cumulative += heights

                        # dummy handle so the legend still works
                        if lbl:
                            ax.bar([], [], label=lbl, color=top_color)

                    else:
                        color = self.palette[idx % len(self.palette)]
                        ax.bar(
                            base_positions,
                            values,
                            bottom=cumulative if stacked else None,
                            width=bar_width,
                            label=lbl,
                            color=color,
                            zorder=2,
                            align="center",
                        )
                        if stacked:
                            cumulative += np.array(values, dtype=float)

            else:
                # grouped bars
                total_width = bar_width
                single_width = total_width / n_series
                offset_start = -total_width / 2 + single_width / 2

                for idx, (lbl, values) in enumerate(series_list):
                    offset = offset_start + idx * single_width

                    if self.theme == "newsroom_dark":
                        top_color = "#64D2FF"
                        bottom_color = "#0077CC"

                        heights = np.array(values, dtype=float)
                        for xi, h in zip(base_positions + offset, heights):
                            if h == 0:
                                continue

                            # invisible base bar for layout
                            ax.bar(
                                xi,
                                h,
                                width=single_width,
                                color="none",
                                edgecolor="none",
                                zorder=1,
                                align="center",
                            )

                            # gradient
                            self._make_vertical_gradient(
                                ax,
                                x0=xi - single_width / 2.0,
                                y0=0,
                                width=single_width,
                                height=h,
                                top_color=top_color,
                                bottom_color=bottom_color,
                                z=2,
                            )

                        # legend handle
                        if lbl:
                            ax.bar([], [], label=lbl, color=top_color)

                    else:
                        color = self.palette[idx % len(self.palette)]
                        ax.bar(
                            base_positions + offset,
                            values,
                            width=single_width,
                            label=lbl,
                            color=color,
                            zorder=2,
                            align="center",
                        )

            # ----------------------------
            # axis limits
            # ----------------------------
            self._apply_axis_limits(ax, xlim, ylim)

            # helper for compact year labels
            def _compact_years(lbls):
                out: List[str] = []
                for i, lab in enumerate(lbls):
                    s = str(lab)
                    try:
                        yr = int(s)
                        if i == 0:
                            out.append(str(yr))
                        else:
                            out.append(str(yr % 100))
                    except Exception:
                        out.append(s)
                return out

            # ----------------------------
            # x axis configuration
            # ----------------------------
            if is_categorical:
                step = self._resolve_x_step(
                    x,
                    x_tick_step=x_tick_step,
                    max_x_ticks=max_x_ticks,
                    auto_x_thinning=auto_x_thinning,
                    rotation=rotation,
                )
                indices = np.arange(len(x))
                visible_idx = indices[::step]
                visible_lbls = [x[i] for i in visible_idx]
                compact_lbls = _compact_years(visible_lbls)

                self._apply_tick_labels(
                    ax,
                    "x",
                    ticks=visible_idx,
                    labels=compact_lbls,
                    rotation=rotation,
                    max_label_width=max_label_width,
                    width_strategy=label_width_strategy,
                    tick_padding=tick_label_pad,
                )

            elif is_datetime:
                self._apply_datetime_x_axis(ax, x, max_x_ticks=max_x_ticks)

            else:
                # numeric axis
                self._apply_numeric_x_axis(
                    ax,
                    x_values=base_positions,
                    x_tick_step=x_tick_step,
                    max_x_ticks=max_x_ticks,
                    x_formatter=x_formatter,
                )

                # restore original labels if we treated numeric-like
                if use_numeric_axis_with_labels and x_tick_labels_forced is not None:
                    compact_lbls = _compact_years(x_tick_labels_forced)
                    self._apply_tick_labels(
                        ax,
                        "x",
                        ticks=base_positions,
                        labels=compact_lbls,
                        rotation=rotation,
                        max_label_width=max_label_width,
                        width_strategy=label_width_strategy,
                        tick_padding=tick_label_pad,
                    )

            # ----------------------------
            # y axis configuration
            # ----------------------------
            self._apply_y_axis(
                ax,
                y_tick_step=y_tick_step,
                max_y_ticks=max_y_ticks,
                y_formatter=y_formatter,
            )

            ax.tick_params(axis="y", which="both", length=0)
            ax.tick_params(
                axis="x",
                which="major",
                pad=1.5,
                length=3,
                width=0.5,
            )
            ax.margins(x=0)

            # ----------------------------
            # finalize + footer
            # ----------------------------
            has_legend = any(l for l, _ in series_list)
            self._finalize_axes(
                ax,
                rotation=rotation,
                has_legend=has_legend,
            )

            self._add_footer(fig)

            # save if requested
            if save_path is not None:
                self.save_figure(
                    fig, save_path, dpi=save_dpi, fmt=save_format, **save_kwargs
                )

            if show:
                plt.show()

            return fig, ax
