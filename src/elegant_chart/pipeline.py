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
``top_n``   ``n``
``pivot``   ``index``, ``columns``, ``values`` (long → wide, duplicates summed)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence, Union

import pandas as pd

from .spec import AGGREGATIONS, FILTER_OPERATORS, StepSpec

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
    return df.sort_values(col, ascending=bool(p.get("ascending", False)), kind="stable").reset_index(
        drop=True
    )


def _top_n(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    try:
        n = int(p.get("n", 10))
    except (TypeError, ValueError):
        raise StepError("N must be a whole number.") from None
    if n < 0:
        raise StepError("N must be zero or more.")
    return df.head(n).reset_index(drop=True)


def _pivot(df: pd.DataFrame, p: Mapping[str, Any]) -> pd.DataFrame:
    index = _need_column(df, p.get("index"))
    columns = _need_column(df, p.get("columns"))
    values = _need_column(df, p.get("values"))
    if len({index, columns, values}) < 3:
        raise StepError("Index, columns and values must be three different columns.")
    wide = df.pivot_table(index=index, columns=columns, values=values, aggfunc="sum", sort=False)
    wide.columns = [str(c) for c in wide.columns]
    return wide.reset_index()


_OPS = {"filter": _filter, "group": _group, "sort": _sort, "top_n": _top_n, "pivot": _pivot}


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
