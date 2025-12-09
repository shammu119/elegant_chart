# elegant_chart/data_mixin.py
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd
from datetime import datetime

from .types import FormatterSpec


class DataMixin:
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
            self._max_y_value = 1.0
        else:
            arr = np.asarray(all_vals, dtype=float)
            finite = arr[np.isfinite(arr)]
            self._max_y_value = float(finite.max()) if finite.size > 0 else 1.0

    def _is_datetime_like(self, value: Any) -> bool:
        from datetime import datetime

        if isinstance(value, datetime):
            return True
        if isinstance(value, pd.Timestamp):
            return True
        try:
            import numpy as np

            return np.issubdtype(type(value), np.datetime64)
        except TypeError:
            return False

    def _resolve_x_step(
        self,
        labels: Sequence[Any],
        x_tick_step: Optional[int] = None,
        max_x_ticks: Optional[int] = None,
        auto_x_thinning: Optional[bool] = None,
        rotation: float = 0,
    ) -> int:
        if x_tick_step is None:
            x_tick_step = self.x_tick_step
        if max_x_ticks is None:
            max_x_ticks = self.max_x_ticks
        if auto_x_thinning is None:
            auto_x_thinning = self.auto_x_thinning

        n = len(labels)
        if n == 0:
            return 1

        if x_tick_step is not None and x_tick_step > 1:
            return int(x_tick_step)

        if max_x_ticks is not None and max_x_ticks > 0 and n > max_x_ticks:
            from math import ceil

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
                from math import ceil

                return max(1, int(ceil(n / max_allowed)))

        return 1
