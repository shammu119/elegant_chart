# elegant_chart/data_mixin.py
from __future__ import annotations

from math import ceil
from datetime import datetime
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

from .types import FormatterSpec  # noqa: F401 — re-exported for mixin consumers


class XPlan(NamedTuple):
    """Resolved x-axis plan: type classification and numeric positions for plotting."""

    is_categorical: bool
    is_datetime: bool
    is_numeric: bool
    positions: np.ndarray
    # True when string labels look numeric AND xlim was given — axis is numeric
    # but tick labels are restored to the original strings.
    use_numeric_axis_with_labels: bool
    x_tick_labels_forced: Optional[List[str]]


class DataMixin:
    # ── series normalisation ──────────────────────────────────────────────

    def _normalize_series(
        self,
        ys: Union[Sequence[Any], Dict[str, Sequence[Any]]],
        labels: Optional[Sequence[Optional[str]]] = None,
    ) -> List[Tuple[Optional[str], List[float]]]:
        series_list: List[Tuple[Optional[str], List[float]]] = []

        if isinstance(ys, dict):
            for lbl, vals in ys.items():
                series_list.append((str(lbl), list(vals)))
            return series_list

        try:
            ys_list = list(ys)  # type: ignore[arg-type]
        except TypeError:
            raise ValueError("ys must be a sequence, dict, or list of sequences")

        if not ys_list:
            raise ValueError("ys cannot be empty")

        first = ys_list[0]
        if not hasattr(first, "__iter__") or isinstance(first, (int, float, np.number)):
            label = labels[0] if labels else None  # type: ignore[index]
            return [(label, list(ys_list))]

        if labels is None:
            labels = [None] * len(ys_list)
        if len(labels) != len(ys_list):
            raise ValueError("Length of labels must match number of series in ys")

        for lbl, arr in zip(labels, ys_list):
            series_list.append((lbl, list(arr)))  # type: ignore[arg-type]

        return series_list

    def _from_dataframe(
        self,
        df: pd.DataFrame,
        x_col: str,
        y_cols: Union[str, Sequence[str]],
    ) -> Tuple[List[Any], Any, List[str]]:
        x = df[x_col].tolist()
        if isinstance(y_cols, str):
            ys = df[y_cols].tolist()
            labels = [y_cols]
        else:
            ys = [df[col].tolist() for col in y_cols]
            labels = list(y_cols)
        return x, ys, labels

    # ── validation ────────────────────────────────────────────────────────

    def _validate_x_nonempty(self, x: Sequence[Any]) -> None:
        if len(x) == 0:
            raise ValueError("x must not be empty")

    def _validate_series_lengths(
        self,
        x: Sequence[Any],
        series_list: List[Tuple[Optional[str], List[float]]],
    ) -> None:
        n = len(x)
        for lbl, vals in series_list:
            if len(vals) != n:
                raise ValueError(
                    f"Series {lbl!r} length {len(vals)} does not match x length {n}"
                )

    def _validate_values(
        self,
        series_list: List[Tuple[Optional[str], List[float]]],
    ) -> None:
        all_vals: List[float] = []
        for _, vals in series_list:
            all_vals.extend(vals)

        if not all_vals:
            raise ValueError("All series are empty")

        arr = np.asarray(all_vals, dtype=float)
        if not np.all(np.isfinite(arr)):
            raise ValueError("ys contains non-finite values (NaN or +/-inf)")

    def _compute_max_y_value(
        self,
        series_list: List[Tuple[Optional[str], List[float]]],
    ) -> None:
        all_vals: List[float] = []
        for _, vals in series_list:
            all_vals.extend(vals)

        if not all_vals:
            self._max_y_value = 1.0  # type: ignore[attr-defined]
        else:
            arr = np.asarray(all_vals, dtype=float)
            finite = arr[np.isfinite(arr)]
            self._max_y_value = float(finite.max()) if finite.size > 0 else 1.0  # type: ignore[attr-defined]

    # ── legend ────────────────────────────────────────────────────────────

    @staticmethod
    def _should_show_legend(
        series_list: List[Tuple[Optional[str], List[float]]],
    ) -> bool:
        """A legend earns its place only when it disambiguates >=2 series.

        A single labelled series should rely on the subtitle to name its
        metric (per the "data-to-ink" principle) rather than spend the
        legend band on a one-item key.
        """
        return sum(1 for lbl, _ in series_list if lbl) >= 2

    # ── datetime detection ────────────────────────────────────────────────

    def _is_datetime_like(self, value: Any) -> bool:
        if isinstance(value, (datetime, pd.Timestamp)):
            return True
        try:
            return bool(np.issubdtype(type(value), np.datetime64))
        except TypeError:
            return False

    # ── x-axis planning (shared between bar and line) ─────────────────────

    def _resolve_x_plan(
        self,
        x: Sequence[Any],
        active_xlim: Optional[Tuple[float, float]],
    ) -> XPlan:
        """
        Classify x values and compute numeric positions for plotting.

        Centralises the x-type detection that was previously duplicated across
        :meth:`~.bar_mixin.BarMixin.bar` and :meth:`~.line_mixin.LineMixin.line`.
        """
        import matplotlib.dates as mdates  # noqa: PLC0415

        first_x = x[0]
        is_categorical = isinstance(first_x, str)
        is_datetime = self._is_datetime_like(first_x)
        is_numeric = not is_categorical and not is_datetime

        use_numeric_axis_with_labels = False
        x_tick_labels_forced: Optional[List[str]] = None

        if is_categorical:
            try:
                numeric_vals = np.array([float(v) for v in x], dtype=float)
                numeric_like = True
            except (ValueError, TypeError):
                numeric_like = False

            if numeric_like and active_xlim is not None:
                is_categorical = False
                is_numeric = True
                use_numeric_axis_with_labels = True
                x_tick_labels_forced = [str(v) for v in x]
                positions = numeric_vals
            else:
                positions = np.arange(len(x), dtype=float)

        elif is_datetime:
            positions = mdates.date2num(x)

        else:
            positions = np.asarray(x, dtype=float)

        return XPlan(
            is_categorical=is_categorical,
            is_datetime=is_datetime,
            is_numeric=is_numeric,
            positions=positions,
            use_numeric_axis_with_labels=use_numeric_axis_with_labels,
            x_tick_labels_forced=x_tick_labels_forced,
        )

    # ── tick-label helpers ────────────────────────────────────────────────

    @staticmethod
    def _compact_years(lbls: List[str], enabled: bool = True) -> List[str]:
        """
        Abbreviate year-string tick labels so only the first shows 4 digits.
        e.g. ["2020","2021","2022"] → ["2020","21","22"]

        Only applied when ``enabled=True``; default is ``False`` (caller must
        opt in) to avoid silently corrupting non-year integer labels like
        ``[1001, 1002]`` → ``["1001", "2"]``.
        """
        if not enabled:
            return [str(l) for l in lbls]

        out: List[str] = []
        for i, lab in enumerate(lbls):
            s = str(lab)
            try:
                yr = int(s)
                out.append(str(yr) if i == 0 else str(yr % 100))
            except (ValueError, TypeError):
                out.append(s)
        return out

    def _resolve_x_step(
        self,
        labels: Sequence[Any],
        x_tick_step: Optional[int] = None,
        max_x_ticks: Optional[int] = None,
        auto_x_thinning: Optional[bool] = None,
        rotation: float = 0,
    ) -> int:
        if x_tick_step is None:
            x_tick_step = self.x_tick_step  # type: ignore[attr-defined]
        if max_x_ticks is None:
            max_x_ticks = self.max_x_ticks  # type: ignore[attr-defined]
        if auto_x_thinning is None:
            auto_x_thinning = self.auto_x_thinning  # type: ignore[attr-defined]

        n = len(labels)
        if n == 0:
            return 1

        if x_tick_step is not None and x_tick_step > 1:
            return int(x_tick_step)

        if max_x_ticks is not None and max_x_ticks > 0 and n > max_x_ticks:
            return max(1, int(ceil(n / max_x_ticks)))

        if auto_x_thinning:
            max_len = max(len(str(l)) for l in labels)
            if max_len <= 4:
                max_allowed = 10
            elif max_len <= 8:
                max_allowed = 8
            elif max_len <= 12:
                max_allowed = 6
            else:
                max_allowed = 4

            if abs(rotation) > 0:
                max_allowed = max(3, max_allowed - 2)

            if n > max_allowed:
                return max(1, int(ceil(n / max_allowed)))

        return 1

    # ── bar width auto-sizing ─────────────────────────────────────────────

    def _auto_bar_width(self, x_plan: "XPlan", n: int) -> float:
        """Return a bar width appropriate for the x-axis type and data density.

        For categorical axes (positions are integers 0..n-1, spacing=1.0) the width
        scales up slightly with bar count so denser charts use the available space.
        For numeric/datetime axes the width is 80 % of the minimum inter-bar gap,
        which naturally adapts to irregular spacing and very tight datetime series.
        """
        if x_plan.is_categorical:
            if n <= 4:
                return 0.50
            if n <= 8:
                return 0.60
            if n <= 15:
                return 0.72
            return 0.82
        # Numeric or datetime — use 80 % of smallest gap between consecutive points
        positions = x_plan.positions
        if len(positions) < 2:
            return 0.7
        gaps = np.diff(positions)
        positive_gaps = gaps[gaps > 0]
        if positive_gaps.size == 0:
            return 0.7
        return float(positive_gaps.min()) * 0.8

    # ── last-render cache ─────────────────────────────────────────────────

    def _store_series(
        self,
        x: Sequence[Any],
        series_list: List[Tuple[Optional[str], List[float]]],
    ) -> None:
        """Cache the most recent render's data so export_data() can access it."""
        self._last_x = list(x)  # type: ignore[attr-defined]
        self._last_series_list = list(series_list)  # type: ignore[attr-defined]

    def export_data(self, path: str) -> None:
        """
        Export the data from the most recent ``bar()`` or ``line()`` call to an
        Excel file (``.xlsx``).

        Parameters
        ----------
        path:
            Destination file path, e.g. ``"output/chart_data.xlsx"``.

        Raises
        ------
        RuntimeError
            If called before any chart has been rendered on this instance.
        ImportError
            If ``openpyxl`` is not installed.

        Example
        -------
        ::

            chart = ElegantChart(title="Revenue")
            chart.bar(x=["Q1", "Q2", "Q3"], ys=[10, 20, 15], show=False)
            chart.export_data("revenue.xlsx")
        """
        if self._last_x is None or self._last_series_list is None:  # type: ignore[attr-defined]
            raise RuntimeError(
                "No chart data to export. Call bar() or line() first."
            )

        try:
            import openpyxl  # noqa: F401, PLC0415
        except ImportError as exc:
            raise ImportError(
                "openpyxl is required for Excel export. "
                "Install it with: pip install openpyxl"
            ) from exc

        data: dict = {"x": self._last_x}  # type: ignore[attr-defined]
        for lbl, vals in self._last_series_list:  # type: ignore[attr-defined]
            col = lbl if lbl else "value"
            # Avoid duplicate column names when multiple unlabelled series exist
            if col in data:
                col = f"{col}_{list(data.keys()).count(col)}"
            data[col] = vals

        pd.DataFrame(data).to_excel(path, index=False)

    # ── shared finalisation ───────────────────────────────────────────────

    def _finalize_and_output(
        self,
        fig: Any,
        ax: Any,
        rotation: float,
        has_legend: bool,
        save_path: Optional[str],
        save_dpi: int,
        save_format: Optional[str],
        show: bool,
        **save_kwargs: Any,
    ) -> None:
        """Call finalize_axes, add_footer, optional save, optional show."""
        self._finalize_axes(ax, rotation=rotation, has_legend=has_legend)  # type: ignore[attr-defined]
        self._add_footer(fig)  # type: ignore[attr-defined]

        if save_path is not None:
            self.save_figure(fig, save_path, dpi=save_dpi, fmt=save_format, **save_kwargs)  # type: ignore[attr-defined]

        import matplotlib.pyplot as plt  # noqa: PLC0415
        if show:
            plt.show()
