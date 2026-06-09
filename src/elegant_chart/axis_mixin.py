# elegant_chart/axis_mixin.py
from typing import Optional, Sequence, Tuple
import textwrap
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import matplotlib.dates as mdates

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
            ax.set_xticklabels(formatted, rotation=rotation)
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

        ax.yaxis.tick_right()
        ax.yaxis.set_label_position("right")
        ax.spines["right"].set_position(("outward", 0))
        ax.spines["left"].set_visible(False)

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

    def _apply_numeric_x_axis(
        self,
        ax: plt.Axes,
        x_values: Sequence[float],
        x_tick_step: Optional[float] = None,
        max_x_ticks: Optional[int] = None,
        x_formatter: Optional[FormatterSpec] = None,
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

    def _apply_datetime_x_axis(
        self,
        ax: plt.Axes,
        x_values,
        max_x_ticks: Optional[int] = None,
    ) -> None:
        locator = mdates.AutoDateLocator(minticks=3, maxticks=max_x_ticks or 7)
        formatter = mdates.AutoDateFormatter(locator)
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)
        ax.figure.autofmt_xdate()
