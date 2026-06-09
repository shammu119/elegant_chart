# elegant_chart/bar_mixin.py
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rc_context

from .types import FormatterSpec
from .data_mixin import DataMixin


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
        # output
        show: bool = True,
        save_path: Optional[str] = None,
        save_dpi: int = 500,
        save_format: Optional[str] = None,
        **save_kwargs: Any,
    ) -> Tuple[plt.Figure, plt.Axes]:
        """Create a bar chart with categorical, numeric, or datetime x values."""

        # ── DataFrame shortcut ────────────────────────────────────────────
        if df is not None:
            if x_col is None or y_cols is None:
                raise ValueError("If df is provided, x_col and y_cols must be set")
            x, ys, labels = self._from_dataframe(df, x_col, y_cols)

        if x is None:
            raise ValueError("x must be provided (or use df + x_col + y_cols)")
        if ys is None:
            raise ValueError("ys must be provided (or use df + x_col + y_cols)")

        # ── validate ──────────────────────────────────────────────────────
        self._validate_x_nonempty(x)
        series_list = self._normalize_series(ys, labels)
        self._validate_series_lengths(x, series_list)
        self._validate_values(series_list)
        self._compute_max_y_value(series_list)
        self._store_series(x, series_list)

        active_xlim = xlim if xlim is not None else self.xlim  # type: ignore[attr-defined]
        x_plan = self._resolve_x_plan(x, active_xlim)
        effective_bar_width = bar_width if bar_width is not None else self._auto_bar_width(x_plan, len(x))

        with rc_context(self._rc):  # type: ignore[attr-defined]
            fig, ax = self._init_figure_and_axes()  # type: ignore[attr-defined]
            self._configure_grid(ax)  # type: ignore[attr-defined]

            base_positions = x_plan.positions

            if x_plan.is_datetime:
                ax.xaxis_date()

            # ── draw bars ─────────────────────────────────────────────────
            n_series = len(series_list)
            val_fmt = self._build_formatter(y_formatter if y_formatter is not None else self.y_formatter)  # type: ignore[attr-defined]

            if stacked or n_series == 1:
                cumulative = np.zeros(len(base_positions))
                for idx, (lbl, values) in enumerate(series_list):
                    color = self.palette[idx % len(self.palette)]  # type: ignore[attr-defined]
                    ax.bar(
                        base_positions,
                        values,
                        bottom=cumulative if stacked else None,
                        width=effective_bar_width,
                        label=lbl,
                        color=color,
                        zorder=2,
                        align="center",
                    )
                    if show_value_labels:
                        for pos, v, cum in zip(base_positions, values, cumulative):
                            bar_top = float(v) + float(cum) if stacked else float(v)
                            ax.text(
                                float(pos), bar_top, val_fmt(float(v), 0),
                                ha="center", va="bottom",
                                fontsize=self._fs(8),  # type: ignore[attr-defined]
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
                    color = self.palette[idx % len(self.palette)]  # type: ignore[attr-defined]
                    ax.bar(
                        base_positions + offset,
                        values,
                        width=single_width,
                        label=lbl,
                        color=color,
                        zorder=2,
                        align="center",
                    )
                    if show_value_labels:
                        for pos, v in zip(base_positions, values):
                            ax.text(
                                float(pos) + offset, float(v), val_fmt(float(v), 0),
                                ha="center", va="bottom",
                                fontsize=self._fs(8),  # type: ignore[attr-defined]
                                color=self.color_text_main,  # type: ignore[attr-defined]
                                zorder=6,
                            )

            # ── axis limits ───────────────────────────────────────────────
            self._apply_axis_limits(ax, xlim, ylim)  # type: ignore[attr-defined]

            # ── x axis ────────────────────────────────────────────────────
            if x_plan.is_categorical:
                step = self._resolve_x_step(
                    x,
                    x_tick_step=x_tick_step,
                    max_x_ticks=max_x_ticks,
                    auto_x_thinning=auto_x_thinning,
                    rotation=rotation,
                )
                indices = np.arange(len(x))
                visible_idx = indices[::step]
                visible_lbls = self._compact_years(
                    [str(x[i]) for i in visible_idx], enabled=compact_years
                )
                self._apply_tick_labels(  # type: ignore[attr-defined]
                    ax, "x",
                    ticks=visible_idx,
                    labels=visible_lbls,
                    rotation=rotation,
                    max_label_width=max_label_width,
                    width_strategy=label_width_strategy,
                    tick_padding=tick_label_pad,
                )

            elif x_plan.is_datetime:
                self._apply_datetime_x_axis(ax, x, max_x_ticks=max_x_ticks)  # type: ignore[attr-defined]

            else:
                self._apply_numeric_x_axis(  # type: ignore[attr-defined]
                    ax,
                    x_values=base_positions,
                    x_tick_step=x_tick_step,
                    max_x_ticks=max_x_ticks,
                    x_formatter=x_formatter,
                )
                if x_plan.use_numeric_axis_with_labels and x_plan.x_tick_labels_forced:
                    tick_lbls = self._compact_years(
                        x_plan.x_tick_labels_forced, enabled=compact_years
                    )
                    self._apply_tick_labels(  # type: ignore[attr-defined]
                        ax, "x",
                        ticks=base_positions,
                        labels=tick_lbls,
                        rotation=rotation,
                        max_label_width=max_label_width,
                        width_strategy=label_width_strategy,
                        tick_padding=tick_label_pad,
                    )

            # ── y axis ────────────────────────────────────────────────────
            self._apply_y_axis(  # type: ignore[attr-defined]
                ax,
                y_tick_step=y_tick_step,
                max_y_ticks=max_y_ticks,
                y_formatter=y_formatter,
            )
            ax.tick_params(axis="y", which="both", length=0)
            ax.tick_params(axis="x", which="major", pad=1.5, length=3, width=0.5)
            ax.margins(x=0)

            # ── finalize + output ─────────────────────────────────────────
            has_legend = any(lbl for lbl, _ in series_list)
            self._finalize_and_output(
                fig, ax,
                rotation=rotation,
                has_legend=has_legend,
                save_path=save_path,
                save_dpi=save_dpi,
                save_format=save_format,
                show=show,
                **save_kwargs,
            )

            return fig, ax
