# elegant_chart/axis_mixin.py
import textwrap
from typing import List, Optional, Sequence, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.ticker import AutoMinorLocator, FixedLocator, FuncFormatter

from ._logging import logger
from .types import FormatterSpec, YFormatter


class AxisMixin:
    def _compact_formatter(self, x: float, pos: int) -> str:
        if abs(x) >= 1e9:
            return f"{x/1e9:.1f}B".rstrip("0").rstrip(".")
        elif abs(x) >= 1e6:
            return f"{x/1e6:.1f}M".rstrip("0").rstrip(".")
        elif abs(x) >= 1e3:
            return f"{x/1e3:.1f}K".rstrip("0").rstrip(".")
        else:
            return f"{x:.0f}"

    def _normalize_by_max_formatter(self, x: float, pos: int) -> str:
        max_y = getattr(self, "_max_y_value", None)
        decimals = getattr(self, "_norm_max_decimals", 0)

        if max_y is None or max_y == 0:
            return ""

        value = x / max_y
        fmt = f"{{:.{decimals}f}}"
        out = fmt.format(value)
        return out.rstrip("0").rstrip(".")

    def _build_formatter(
        self, spec: FormatterSpec, default: str = "compact"
    ) -> FuncFormatter:
        if spec is None:
            spec = default

        if isinstance(spec, tuple) and spec[0] == YFormatter.NORM_MAX:
            self._norm_max_decimals = int(spec[1])
            return FuncFormatter(self._normalize_by_max_formatter)

        if spec == YFormatter.COMPACT or spec == "compact":
            return FuncFormatter(self._compact_formatter)

        if spec == YFormatter.PLAIN or spec == "plain":
            return FuncFormatter(lambda x, pos: f"{x:g}")

        if spec == YFormatter.PERCENT or spec == "percent":
            return FuncFormatter(lambda x, pos: f"{x * 100:g}%")

        if isinstance(spec, str):
            return FuncFormatter(lambda x, pos, fmt=spec: fmt.format(x=x))

        if callable(spec):
            return FuncFormatter(spec)

        return FuncFormatter(self._compact_formatter)

    def _format_tick_label_width(
        self,
        label: Optional[str],
        max_width: Optional[int] = None,
        strategy: str = "wrap",
        placeholder: str = "…",
    ) -> str:
        """
        Constrain a tick label to a target width.

        Parameters
        ----------
        label:
            The incoming tick label. ``None`` values are converted to an empty string.
        max_width:
            Maximum character width allowed. ``None`` leaves the label untouched.
        strategy:
            Either ``"wrap"`` to split into multiple lines or ``"truncate"`` to shorten
            with an ellipsis.
        placeholder:
            Ellipsis placeholder used when ``strategy == "truncate"``.
        """

        if label is None:
            label = ""

        text = str(label)
        if max_width is None or max_width <= 0 or len(text) <= max_width:
            return text

        if strategy == "truncate":
            return textwrap.shorten(text, width=max_width, placeholder=placeholder)

        wrapped = textwrap.wrap(text, width=max_width)
        return "\n".join(wrapped) if wrapped else text

    def _apply_tick_labels(
        self,
        ax: plt.Axes,
        axis: str,
        ticks: Sequence[float],
        labels: Sequence[Optional[str]],
        rotation: float = 0,
        max_label_width: Optional[int] = None,
        width_strategy: str = "wrap",
        tick_padding: Optional[float] = None,
    ) -> None:
        formatted = [
            self._format_tick_label_width(
                lbl, max_width=max_label_width, strategy=width_strategy
            )
            for lbl in labels
        ]

        if axis == "x":
            ax.set_xticks(ticks)
            ax.set_xticklabels(formatted, rotation=rotation, ha="center")
            if tick_padding is not None:
                ax.tick_params(axis="x", which="major", pad=tick_padding)
        elif axis == "y":
            ax.set_yticks(ticks)
            ax.set_yticklabels(formatted, rotation=rotation)
            if tick_padding is not None:
                ax.tick_params(axis="y", which="major", pad=tick_padding)
        else:
            raise ValueError("axis must be 'x' or 'y'")

    def _apply_y_axis(
        self,
        ax: plt.Axes,
        y_tick_step: Optional[float] = None,
        max_y_ticks: Optional[int] = None,
        y_formatter: Optional[FormatterSpec] = None,
    ) -> None:
        if y_tick_step is None:
            y_tick_step = self.y_tick_step
        if max_y_ticks is None:
            max_y_ticks = self.max_y_ticks
        if y_formatter is None:
            y_formatter = self.y_formatter

        ax.yaxis.set_major_formatter(self._build_formatter(y_formatter))

        # Orient the axis to the configured side.
        if self.y_axis_side == "right":  # type: ignore[attr-defined]
            ax.yaxis.tick_right()
            ax.yaxis.set_label_position("right")

        if self.y_tick_labels_inside:  # type: ignore[attr-defined]
            # Custom text labels drawn by _draw_economist_ytick_labels; suppress matplotlib's.
            ax.tick_params(axis="y", which="both", length=0, labelleft=False, labelright=False)
        else:
            # Standard matplotlib labels outside the axes on the active side.
            ax.tick_params(axis="y", which="both", length=0)

        if y_tick_step is not None:
            ymin, ymax = ax.get_ylim()
            if ymin == ymax:
                ymin -= 0.5
                ymax += 0.5
                ax.set_ylim(ymin, ymax)
            start = np.floor(ymin / y_tick_step) * y_tick_step
            end = np.ceil(ymax / y_tick_step) * y_tick_step
            ticks = np.arange(start, end + 0.5 * y_tick_step, y_tick_step)
            ax.set_yticks(ticks)
        elif max_y_ticks is not None:
            ax.locator_params(axis="y", nbins=max_y_ticks)

    def _draw_economist_ytick_labels(
        self,
        ax: plt.Axes,
        secondary: bool = False,
    ) -> list:
        """Render y-axis tick labels inside the plot area (Economist style).

        Works for both the primary (left) and secondary (right, secondary=True) y-axis so
        that a twinx() secondary axis receives the same treatment. Each label sits just
        inside its respective edge — right-aligned near the right edge for the framework's
        default right-hand axis, left-aligned near the left edge otherwise — floating
        just *above* its gridline. Keeping labels inside the plot frees the outer margin
        entirely for data (see FigureMixin._finalize_axes' subplots_adjust).

        Returns the list of created Text artists so callers can measure their
        rendered extent (e.g. to detect overlap with plotted data).
        """
        formatter = ax.yaxis.get_major_formatter()
        locator = ax.yaxis.get_major_locator()
        ymin, ymax = ax.get_ylim()
        ticks = locator.tick_values(ymin, ymax)
        visible_ticks = [t for t in ticks if ymin <= t <= ymax]

        # x is in axes fraction (0=left edge, 1=right edge); y is in data coordinates.
        pad = 0.01
        x_pos = 1.0 - pad if secondary else pad
        h_align = "right" if secondary else "left"
        transform = ax.get_yaxis_transform()

        texts = []
        for tick_val in visible_ticks:
            label_str = formatter(tick_val, 0)
            texts.append(
                ax.text(
                    x_pos,
                    tick_val,
                    label_str,
                    transform=transform,
                    ha=h_align,
                    va="bottom",
                    fontsize=self._ts("tick_label"),  # type: ignore[attr-defined]
                    color=self.color_tick,  # type: ignore[attr-defined]
                    zorder=5,
                    clip_on=False,
                )
            )
        return texts

    def _apply_numeric_x_axis(
        self,
        ax: plt.Axes,
        x_values: Sequence[float],
        x_tick_step: Optional[float] = None,
        max_x_ticks: Optional[int] = None,
        x_formatter: Optional[FormatterSpec] = None,
        minor_ticks: Optional[int] = None,
    ) -> None:
        if x_tick_step is None:
            x_tick_step = self.x_tick_step
        if max_x_ticks is None:
            max_x_ticks = self.max_x_ticks

        x_arr = np.asarray(x_values, dtype=float)
        if x_arr.size == 0:
            return

        xmin, xmax = float(x_arr.min()), float(x_arr.max())

        if x_tick_step is not None:
            if xmin == xmax:
                xmin -= 0.5
                xmax += 0.5
                ax.set_xlim(xmin, xmax)
            start = np.floor(xmin / x_tick_step) * x_tick_step
            end = np.ceil(xmax / x_tick_step) * x_tick_step
            ticks = np.arange(start, end + 0.5 * x_tick_step, x_tick_step)
            ax.set_xticks(ticks)
        elif max_x_ticks is not None:
            ax.locator_params(axis="x", nbins=max_x_ticks)

        if x_formatter is not None:
            ax.xaxis.set_major_formatter(
                self._build_formatter(x_formatter, default="plain")
            )

        if minor_ticks:
            # AutoMinorLocator(n) places (n-1) evenly-spaced minor ticks between
            # each pair of major ticks, so minor_ticks=1 gives a single midpoint tick.
            ax.xaxis.set_minor_locator(AutoMinorLocator(minor_ticks + 1))
            ax.tick_params(
                axis="x", which="minor", direction="out",
                length=self._px(2.5), width=self._px(0.4),  # type: ignore[attr-defined]
                colors=self.color_subtitle,  # type: ignore[attr-defined]
            )

    def _apply_datetime_x_axis(
        self,
        ax: plt.Axes,
        x_values,
        max_x_ticks: Optional[int] = None,
        data_bounds: Optional[Tuple[float, float]] = None,
        minor_ticks: Optional[int] = None,
        date_format: Optional[str] = None,
    ) -> None:
        auto_locator = mdates.AutoDateLocator(minticks=3, maxticks=max_x_ticks or 7)
        formatter = (
            mdates.DateFormatter(date_format)
            if date_format
            else mdates.AutoDateFormatter(auto_locator)
        )
        ax.xaxis.set_major_formatter(formatter)

        # Endpoint pinning forces the exact first/last data points in as labeled
        # major ticks so the axis is always labeled at its true range — but with
        # an explicit date_format those endpoints are arbitrary dates that don't
        # align to the requested cadence (e.g. a "%Y" axis would gain a stray
        # mid-year label). Skip pinning in that case and let the locator place
        # clean, evenly-spaced ticks; the true range stays anchored by the
        # unlabeled boundary tick marks (_draw_x_boundary_ticks).
        pin_endpoints = data_bounds is not None and not date_format

        majors: Optional[List[float]] = None
        if data_bounds is not None:
            lo, hi = data_bounds
            # AutoDateLocator.tick_values() requires datetime bounds (it
            # internally diffs them with relativedelta), not raw date2num
            # floats — convert. Note tick_values() already returns its
            # result in date2num scale, so no further conversion is needed.
            dmin, dmax = mdates.num2date(lo), mdates.num2date(hi)
            interior = [
                t for t in auto_locator.tick_values(dmin, dmax)
                if lo < t < hi
            ]

            if pin_endpoints:
                # Take the auto cadence's interior ticks, drop any that crowd
                # the endpoints, then pin the exact data bounds as the
                # first/last major ticks.
                span = hi - lo
                if span > 0:
                    edge_margin = span * 0.04
                    interior = [
                        t for t in interior
                        if (t - lo) > edge_margin and (hi - t) > edge_margin
                    ]
                majors = sorted({lo, *interior, hi})
                ax.xaxis.set_major_locator(FixedLocator(majors))
                logger.debug("Datetime major ticks (incl. endpoints): %s", majors)
            else:
                majors = sorted(interior)
                ax.xaxis.set_major_locator(FixedLocator(majors))
                logger.debug("Datetime major ticks: %s", majors)

        if majors is None:
            ax.xaxis.set_major_locator(auto_locator)

        if minor_ticks and majors and len(majors) >= 2:
            minors: List[float] = []
            for a, b in zip(majors[:-1], majors[1:]):
                step = (b - a) / (minor_ticks + 1)
                minors.extend(a + step * i for i in range(1, minor_ticks + 1))
            ax.xaxis.set_minor_locator(FixedLocator(minors))
            ax.tick_params(
                axis="x", which="minor", direction="out",
                length=self._px(2.5), width=self._px(0.4),  # type: ignore[attr-defined]
                colors=self.color_subtitle,  # type: ignore[attr-defined]
            )

        # Keep labels horizontal (Economist style); avoid autofmt_xdate(),
        # which rotates and right-aligns datetime labels. Per-label
        # left/center/right alignment of the edge labels is handled by
        # _align_x_edge_labels() once layout has settled.
        ax.tick_params(axis="x", labelrotation=0)

    def _align_x_edge_labels(self, ax: plt.Axes) -> None:
        """Left-align the first major x-tick label, right-align the last.

        The default ``ha="center"`` works for interior ticks but lets the
        first label bleed past the left edge of the plot (and the last
        bleed past the right). Anchoring the leftmost visible major tick's
        label to its left edge — and the rightmost to its right edge — keeps
        every label within the plot area, which matters most once
        ``_apply_datetime_x_axis``/``_apply_numeric_x_axis`` pin major ticks
        at the exact data bounds.
        """
        xlim = ax.get_xlim()
        lo, hi = min(xlim), max(xlim)
        ticks = list(ax.xaxis.get_majorticklocs())
        visible = [t for t in ticks if lo - 1e-9 <= t <= hi + 1e-9]
        if len(visible) < 2:
            return

        tick_min, tick_max = min(visible), max(visible)
        for lbl, tick in zip(ax.get_xticklabels(), ticks):
            if tick == tick_min:
                lbl.set_horizontalalignment("left")
            elif tick == tick_max:
                lbl.set_horizontalalignment("right")
            else:
                lbl.set_horizontalalignment("center")

    def _draw_x_boundary_ticks(self, ax: plt.Axes) -> None:
        """Draw short downward tick marks at the exact x-axis start and end.

        Thinned categorical ticks, ``AutoDateLocator`` ticks, and step-based
        numeric ticks all commonly land short of the true data bounds, leaving
        the baseline's endpoints unmarked. These two manual segments — sized
        and colored to match the regular x-ticks (``length=_px(5)``,
        ``width=_px(0.5)``, set via ``ax.tick_params`` in bar/line mixins) —
        sharply anchor the data range regardless of x-axis type. Called last
        from ``_finalize_axes``, after layout has settled, so the axes height
        used to convert the point-based tick length to an axes-fraction is final.
        """
        fig = ax.get_figure()
        tick_len_frac = 0.02  # fallback if renderer geometry is unavailable
        try:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            axes_height_px = ax.get_window_extent(renderer).height
            tick_len_px = self._px(5) / 72.0 * fig.dpi  # type: ignore[attr-defined]
            if axes_height_px > 0:
                tick_len_frac = tick_len_px / axes_height_px
        except Exception:
            logger.debug("_draw_x_boundary_ticks geometry step failed", exc_info=True)

        # Anchor at the *data* bounds, not ax.get_xlim() — the upper xlim is
        # padded (see FigureMixin._finalize_axes) to clear the inside y-tick
        # labels, so the right boundary tick should sit at the true last
        # data point rather than out in the empty padding.
        bounds = getattr(self, "_x_data_bounds", None) or ax.get_xlim()

        # Skip a boundary tick if a major tick already lands close to it —
        # avoids a "double tooth" of two near-adjacent ticks at the edges.
        xlim = ax.get_xlim()
        span = abs(xlim[1] - xlim[0])
        edge_margin = span * 0.04 if span > 0 else 0
        majors = ax.xaxis.get_majorticklocs()
        bounds = [
            x for x in bounds
            if not any(abs(x - m) <= edge_margin for m in majors)
        ]

        ymin, ymax = ax.get_ylim()
        if ymin < 0 < ymax:
            # The baseline has been relocated to data y=0 (see
            # FigureMixin._finalize_axes), so anchor the boundary ticks there
            # too, in data coordinates — converting the axes-fraction tick
            # length to an equivalent data-y delta.
            transform = ax.transData
            y0, y1 = 0.0, -tick_len_frac * (ymax - ymin)
        else:
            # x: data coordinates; y: axes fraction (0 = baseline, going downward).
            transform = ax.get_xaxis_transform()
            y0, y1 = 0.0, -tick_len_frac

        for x in bounds:
            ax.add_line(
                Line2D(
                    [x, x],
                    [y0, y1],
                    transform=transform,
                    color=self.color_tick,  # type: ignore[attr-defined]
                    linewidth=self._px(0.5),  # type: ignore[attr-defined]
                    clip_on=False,
                    zorder=3,
                )
            )
