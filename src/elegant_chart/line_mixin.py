# elegant_chart/line_mixin.py
from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import rc_context

from .types import FormatterSpec
from .data_mixin import DataMixin


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
        markers: bool = True,
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
        show: bool = True,
        save_path: Optional[str] = None,
        save_dpi: int = 500,
        save_format: Optional[str] = None,
        **save_kwargs: Any,
    ) -> Tuple[plt.Figure, plt.Axes]:
        """Create a line chart with categorical, numeric, or datetime x values."""

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

        # Resolve linewidth: None → auto-scale from reference; explicit float → honour as-is.
        effective_lw = linewidth if linewidth is not None else self._px(0.8)  # type: ignore[attr-defined]

        with rc_context(self._rc):  # type: ignore[attr-defined]
            fig, ax = self._init_figure_and_axes()  # type: ignore[attr-defined]
            self._configure_grid(ax)  # type: ignore[attr-defined]

            x_positions = x_plan.positions

            if x_plan.is_datetime:
                ax.xaxis_date()

            # ── draw lines ────────────────────────────────────────────────
            val_fmt = self._build_formatter(y_formatter if y_formatter is not None else self.y_formatter)  # type: ignore[attr-defined]

            for idx, (lbl, values) in enumerate(series_list):
                color = self.palette[idx % len(self.palette)]  # type: ignore[attr-defined]
                if markers:
                    ax.plot(
                        x_positions, values,
                        label=lbl,
                        color=color,
                        linewidth=effective_lw,
                        marker="o",
                        markersize=self._px(3),  # type: ignore[attr-defined]
                        zorder=2,
                    )
                else:
                    ax.plot(
                        x_positions, values,
                        label=lbl,
                        color=color,
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
                            fontsize=self._fs(8),  # type: ignore[attr-defined]
                            color=self.color_text_main,  # type: ignore[attr-defined]
                            zorder=6,
                        )

            # ── axis limits ───────────────────────────────────────────────
            self._apply_axis_limits(ax, xlim, ylim)  # type: ignore[attr-defined]
            self._apply_y_axis(  # type: ignore[attr-defined]
                ax,
                y_tick_step=y_tick_step,
                max_y_ticks=max_y_ticks,
                y_formatter=y_formatter,
            )

            ax.tick_params(axis="y", which="both", length=0)
            ax.tick_params(axis="x", which="major", pad=self._px(1.5), length=self._px(3), width=self._px(0.5))
            ax.margins(x=0)

            if active_xlim is None and not x_plan.is_datetime:
                ax.set_xlim(float(x_positions.min()), float(x_positions.max()))

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
                    x_values=x_positions,
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
                        ticks=x_positions,
                        labels=tick_lbls,
                        rotation=rotation,
                        max_label_width=max_label_width,
                        width_strategy=label_width_strategy,
                        tick_padding=tick_label_pad,
                    )

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
