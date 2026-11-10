# elegant_chart/pipeline.py
"""
Reshape pipeline — ``apply_steps(df, steps)``.

Each step is one small pandas operation.  The pipeline stops at the first
failing step: that step carries its error message, the steps after it are
marked ``skipped``, and the returned frame is the output of the last step that
succeeded.  Steps are never silently skipped, because a skipped filter could
produce a wrong-but-plausible chart.

Supported ops (``StepSpec.op`` / ``params``):

``filter``  ``column``, ``operator`` (``= ≠ > ≥ < ≤ in``), ``value``
``group``   ``by`` (list), ``agg`` (sum|mean|count|min|max), ``columns`` (list, optional)
``sort``    ``column``, ``ascending`` (bool)
``top_n``   ``n``, ``which`` (top|bottom), ``column`` (optional: rank by it)
``pivot``   ``index``, ``columns``, ``values`` (long → wide, duplicates summed)
``date_filter``  ``column``, ``years`` ([from, to]), ``months`` (list of 1-12)
``snap_dates``   ``column``, ``to`` (one of DATE_SNAPS)
``resample``     ``column``, ``period`` (month|quarter|year), ``agg`` (RESAMPLE_AGGS)
``scale``        ``columns``, ``unit`` (SCALE_UNITS), ``factor`` (for "custom")
``change``       ``columns``, ``kind`` (CHANGE_KINDS), ``date_column`` (for "yoy")
``rolling``      ``columns``, ``window``
``rename``       ``column``, ``to``

Steps that take ``columns`` treat a blank list as every number column except
year-like whole numbers (``2021``), which are labels rather than values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Union

import pandas as pd

from .spec import (
    AGGREGATIONS,
    CHANGE_KINDS,
    DATE_SNAPS,
    FILTER_OPERATORS,
    PERIODS,
    RESAMPLE_AGGS,
    SCALE_UNITS,
    StepSpec,
)

SCALE_FACTORS = {"hundreds": 100.0, "thousands": 1e3, "millions": 1e6, "billions": 1e9}

StepLike = Union[StepSpec, Mapping[str, Any]]


@dataclass
class StepResult:
    status: str  # "ok" | "error" | "skipped"
    error: Optional[str] = None
    rows: Optional[int] = None


@dataclass
class PipelineResult:
    df: pd.DataFrame
    steps: list[StepResult] = field(default_factory=list)
    failed_index: Optional[int] = None

    @property
    def ok(self) -> bool:
        return self.failed_index is None


class StepError(ValueError):
    """A step's parameters don't fit the data it receives."""


def apply_steps(df: pd.DataFrame, steps: Sequence[StepLike]) -> PipelineResult:
    """Apply ``steps`` to ``df`` in order.  ``df`` is never mutated."""
    current = df
    results: list[StepResult] = []
    failed: Optional[int] = None
    for i, raw in enumerate(steps):
        if failed is not None:
            results.append(StepResult("skipped"))
            continue
        op, params = _unpack(raw)
        try:
            current = apply_step(current, op, params)
        except Exception as exc:  # noqa: BLE001 — every failure is shown inline on the step
            failed = i
            results.append(StepResult("error", error=_message(exc)))
            continue
        results.append(StepResult("ok", rows=len(current)))
    return PipelineResult(df=current, steps=results, failed_index=failed)


def apply_step(df: pd.DataFrame, op: str, params: Mapping[str, Any]) -> pd.DataFrame:
    fn = _OPS.get(op)
    if fn is None:
        raise StepError(f"Unknown step '{op}'.")
    return fn(df, params)


# ── ops ───────────────────────────────────────────────────────────────────────


def _filter(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    col = _need_column(df, p.get("column"))
    op = p.get("operator", "=")
    if op not in FILTER_OPERATORS:
        raise StepError(f"Unknown operator '{op}'.")
    series = df[col]
    raw = p.get("value")
    if op == "in":
        items = raw if isinstance(raw, (list, tuple)) else str(raw or "").split(",")
        values = [_coerce(series, v.strip() if isinstance(v, str) else v) for v in items]
        values = [v for v in values if not (isinstance(v, str) and v == "")]
        mask = series.isin(values)
    else:
        value = _coerce(series, raw)
        mask = {
            "=": lambda: series == value,
            "≠": lambda: series != value,
            ">": lambda: series > value,
            "≥": lambda: series >= value,
            "<": lambda: series < value,
            "≤": lambda: series <= value,
        }[op]()
    return df[mask].reset_index(drop=True)


def _group(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    by = _as_list(p.get("by"))
    if not by:
        raise StepError("Choose at least one column to group by.")
    for c in by:
        _need_column(df, c)
    agg = p.get("agg", "sum")
    if agg not in AGGREGATIONS:
        raise StepError(f"Unknown aggregation '{agg}'.")
    cols = _as_list(p.get("columns"))
    for c in cols:
        _need_column(df, c)
    grouped = df.groupby(by, sort=False, dropna=False)
    if agg == "count":
        if cols:
            out = grouped[cols].count()
        else:
            out = grouped.size().to_frame("count")
    else:
        if not cols:
            cols = [c for c in df.select_dtypes("number").columns if c not in by]
            if not cols:
                raise StepError("No numeric columns to aggregate.")
        out = grouped[cols].agg(agg)
    return out.reset_index()


def _sort(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    col = _need_column(df, p.get("column"))
    ascending = bool(p.get("ascending", False))
    return df.sort_values(col, ascending=ascending, kind="stable").reset_index(drop=True)


def _top_n(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    n = _whole_number(p.get("n", 10), "N", minimum=0)
    which = p.get("which") or "top"
    if which not in ("top", "bottom"):
        raise StepError(f"Unknown choice '{which}'; use top or bottom.")
    col = p.get("column")
    if col not in (None, ""):
        _need_column(df, col)
        ranked = df.sort_values(col, ascending=which == "bottom", kind="stable")
        return ranked.head(n).reset_index(drop=True)
    return (df.head(n) if which == "top" else df.tail(n)).reset_index(drop=True)


def _date_filter(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    col = _need_column(df, p.get("column"))
    s = df[col]
    is_date = pd.api.types.is_datetime64_any_dtype(s)
    if not is_date and not is_year_numbers(s):
        raise StepError(f"'{col}' holds neither dates nor year numbers.")
    year = s.dt.year if is_date else s
    mask = pd.Series(True, index=df.index)
    years = _as_list(p.get("years"))
    if years:
        lo, hi = (_whole_number(v, "Year") for v in (min(years), max(years)))
        mask &= year.between(lo, hi)
    months = [_whole_number(m, "Month") for m in _as_list(p.get("months"))]
    if months:
        if not is_date:
            raise StepError(f"'{col}' holds year numbers, so it has no months to pick.")
        mask &= s.dt.month.isin(months)
    return df[mask].reset_index(drop=True)


def _snap_dates(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    col = _need_dates(df, p.get("column"))
    to = p.get("to") or "month_end"
    if to not in DATE_SNAPS:
        raise StepError(f"Unknown date position '{to}'.")
    out = df.copy()
    out[col] = snap(df[col], to)
    return out


def snap(dates: pd.Series, to: str) -> pd.Series:
    """Move each date to the start or end of its month, quarter or year."""
    d = dates.dt.normalize()
    unit, edge = to.split("_")
    if edge == "start":
        return d.dt.to_period({"month": "M", "quarter": "Q", "year": "Y"}[unit]).dt.to_timestamp()
    offset = {"month": pd.offsets.MonthEnd(0), "quarter": pd.offsets.QuarterEnd(0)}
    return d + offset.get(unit, pd.offsets.YearEnd(0))


def _resample(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    col = _need_dates(df, p.get("column"))
    period = p.get("period") or "year"
    if period not in PERIODS:
        raise StepError(f"Unknown period '{period}'.")
    agg = p.get("agg") or "sum"
    if agg not in RESAMPLE_AGGS:
        raise StepError(f"Unknown way to combine '{agg}'.")
    nums = [c for c in df.select_dtypes("number").columns if c != col]
    if not nums:
        raise StepError("No number columns to combine.")
    groups = [c for c in df.columns if c != col and c not in nums]
    ordered = df.sort_values(col, kind="stable").copy()
    ordered[col] = snap(ordered[col], f"{period}_end")
    out = ordered.groupby([col, *groups], sort=True, dropna=False)[nums].agg(agg)
    return out.reset_index()


def _scale(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    unit = p.get("unit") or "thousands"
    if unit not in SCALE_UNITS:
        raise StepError(f"Unknown unit '{unit}'.")
    factor = SCALE_FACTORS.get(unit) if unit != "custom" else p.get("factor")
    try:
        factor = float(factor)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise StepError("Type the number to divide by.") from None
    if factor == 0:
        raise StepError("Divide by a number other than zero.")
    out = df.copy()
    for c in _value_columns(df, p.get("columns")):
        out[c] = df[c] / factor
    return out


def _change(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    kind = p.get("kind") or "pct_prev"
    if kind not in CHANGE_KINDS:
        raise StepError(f"Unknown kind of change '{kind}'.")
    date_col = p.get("date_column") or None
    cols = _value_columns(df, p.get("columns"), exclude=(date_col,))
    values = df[cols].astype(float)
    if kind == "index":
        base = values.apply(lambda s: s.dropna().iloc[0] if s.notna().any() else float("nan"))
        if bool((base == 0).any()):
            raise StepError("A first value is 0, so it cannot be the base of an index.")
        changed = values / base * 100
    elif kind == "diff_prev":
        changed = values.diff()
    else:
        periods = 1 if kind == "pct_prev" else _periods_per_year(df, date_col)
        changed = values.pct_change(periods=periods, fill_method=None) * 100
    out = df.copy()
    out[cols] = changed
    if kind != "index":
        out = out[changed.notna().any(axis=1)]
    return out.reset_index(drop=True)


def _rolling(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    window = _whole_number(p.get("window", 3), "Window", minimum=1)
    cols = _value_columns(df, p.get("columns"))
    averaged = df[cols].astype(float).rolling(window, min_periods=window).mean()
    out = df.copy()
    out[cols] = averaged
    return out[averaged.notna().any(axis=1)].reset_index(drop=True)


def _rename(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    col = _need_column(df, p.get("column"))
    to = str(p.get("to") or "").strip()
    if not to:
        raise StepError("Type the new name.")
    if to != col and to in df.columns:
        raise StepError(f"There is already a column called '{to}'.")
    return df.rename(columns={col: to})


def _pivot(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    index = _need_column(df, p.get("index"))
    columns = _need_column(df, p.get("columns"))
    values = _need_column(df, p.get("values"))
    if len({index, columns, values}) < 3:
        raise StepError("Index, columns and values must be three different columns.")
    wide = df.pivot_table(index=index, columns=columns, values=values, aggfunc="sum", sort=False)
    wide.columns = [str(c) for c in wide.columns]
    return wide.reset_index()


_OPS = {
    "filter": _filter,
    "group": _group,
    "sort": _sort,
    "top_n": _top_n,
    "pivot": _pivot,
    "date_filter": _date_filter,
    "snap_dates": _snap_dates,
    "resample": _resample,
    "scale": _scale,
    "change": _change,
    "rolling": _rolling,
    "rename": _rename,
}


# ── helpers ───────────────────────────────────────────────────────────────────


def _unpack(step: StepLike) -> tuple[str, Mapping[str, Any]]:
    if isinstance(step, StepSpec):
        return step.op, step.params
    return step.get("op", ""), step.get("params") or {}


def _need_column(df: pd.DataFrame, col: Any) -> Any:
    if col is None or col == "":
        raise StepError("Choose a column.")
    if col not in df.columns:
        raise StepError(f"Column '{col}' is not in the data at this step.")
    return col


def _need_dates(df: pd.DataFrame, col: Any) -> Any:
    _need_column(df, col)
    if not pd.api.types.is_datetime64_any_dtype(df[col]):
        raise StepError(f"'{col}' is not a date column.")
    return col


def _whole_number(value: Any, name: str, minimum: Optional[int] = None) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise StepError(f"{name} must be a whole number.") from None
    if minimum is not None and n < minimum:
        raise StepError(f"{name} must be {minimum} or more.")
    return n


def is_year_numbers(s: pd.Series) -> bool:
    if pd.api.types.is_bool_dtype(s) or not pd.api.types.is_numeric_dtype(s):
        return False
    v = s.dropna()
    return not v.empty and bool(((v % 1 == 0) & v.between(1800, 2200)).all())


def value_columns(df: pd.DataFrame) -> list:
    """Number columns that hold values (year-like whole numbers are labels)."""
    return [
        c
        for c in df.select_dtypes("number").columns
        if not pd.api.types.is_bool_dtype(df[c]) and not is_year_numbers(df[c])
    ]


def _value_columns(df: pd.DataFrame, chosen: Any, exclude: Sequence[Any] = ()) -> list:
    cols = _as_list(chosen)
    for c in cols:
        _need_column(df, c)
        if not pd.api.types.is_numeric_dtype(df[c]):
            raise StepError(f"'{c}' is not a number column.")
    if not cols:
        cols = [c for c in value_columns(df) if c not in exclude]
    if not cols:
        raise StepError("No number columns to change.")
    return cols


def _periods_per_year(df: pd.DataFrame, date_col: Any) -> int:
    if date_col is None:
        found = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        found += [c for c in df.columns if is_year_numbers(df[c])]
        if not found:
            raise StepError("Choose the date column, so a year earlier can be found.")
        date_col = found[0]
    s = df[_need_column(df, date_col)]
    if not pd.api.types.is_datetime64_any_dtype(s):
        if is_year_numbers(s):
            return 1
        raise StepError(f"'{date_col}' holds neither dates nor year numbers.")
    gap = s.dropna().sort_values().diff().dt.days.median()
    if pd.isna(gap):
        raise StepError("Need at least two dates to compare with a year earlier.")
    for limit, periods in ((2, 365), (10, 52), (40, 12), (100, 4)):
        if gap <= limit:
            return periods
    return 1


def _as_list(value: Any) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _coerce(series: pd.Series, value: Any) -> Any:
    """Cast a (usually string) widget value to the column's type."""
    if value is None:
        return value
    if pd.api.types.is_bool_dtype(series):
        if isinstance(value, str):
            return value.strip().lower() in ("true", "1", "yes")
        return bool(value)
    if pd.api.types.is_numeric_dtype(series):
        try:
            return float(value)
        except (TypeError, ValueError):
            raise StepError(f"'{value}' is not a number, but the column is numeric.") from None
    if pd.api.types.is_datetime64_any_dtype(series):
        try:
            return pd.Timestamp(value)
        except (TypeError, ValueError):
            raise StepError(f"'{value}' is not a date.") from None
    if isinstance(value, str):
        return value
    return value


def _message(exc: Exception) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    if isinstance(exc, KeyError):
        text = f"Column {text} is not in the data at this step."
    return text
