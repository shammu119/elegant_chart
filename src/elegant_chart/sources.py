# elegant_chart/sources.py
"""
Data sources for Chart Studio (and any other caller).

- :func:`load_mma_series` — MMA Statistics API by series ID, via the existing
  :func:`elegant_chart.get_api_data.get_series_df` (same token resolution and
  Excel cache; the token never passes through this module).
- :func:`read_uploaded` / :func:`list_sheets` — CSV or Excel bytes.
"""

from __future__ import annotations

import io
import os
from typing import Optional

import pandas as pd


def is_excel(name: str) -> bool:
    return os.path.splitext(name or "")[1].lower() in (".xlsx", ".xlsm", ".xls")


def list_sheets(data: bytes) -> list[str]:
    """Sheet names of an Excel workbook given as bytes."""
    with pd.ExcelFile(io.BytesIO(data)) as xl:
        return [str(s) for s in xl.sheet_names]


def read_uploaded(data: bytes, name: str, sheet: Optional[str] = None) -> pd.DataFrame:
    """Parse uploaded CSV or Excel bytes into a DataFrame (date columns detected)."""
    if is_excel(name):
        df = pd.read_excel(io.BytesIO(data), sheet_name=sheet if sheet is not None else 0)
        return parse_date_columns(df)  # cells typed as dates already arrive as datetimes
    if os.path.splitext(name or "")[1].lower() in (".csv", ".txt", ""):
        return parse_date_columns(pd.read_csv(io.BytesIO(data)))
    raise ValueError(f"Unsupported file type: {name}. Use .csv or .xlsx.")


_ISO_DATE = r"^\d{4}-\d{2}-\d{2}([ T].*)?$"

# Tried in order; the first format that parses *every* value wins.  Each is a
# strict strptime pattern, so there is no silent guessing.  For all-numeric
# day/month dates the day-first pattern comes first (the local convention) and
# month-first is only used when the data rules day-first out (e.g. 01/31/2024).
_DATE_FORMATS = (
    "%Y-%m",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%d.%m.%Y",
    "%b %Y",
    "%B %Y",
    "%b-%y",
    "%b-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%d-%b-%Y",
    "%d-%b-%y",
    "%b %d, %Y",
    "%B %d, %Y",
)


def _detect_date_format(text: pd.Series) -> Optional[str]:
    """Return ``"ISO8601"`` or a strptime format that parses every value, else None."""
    uniques = pd.Series(text.unique())  # long-format data repeats dates; test each once
    if uniques.str.match(_ISO_DATE).all():
        candidates: tuple[str, ...] = ("ISO8601",)
    elif not uniques.str.contains(r"\d").all():
        return None  # "Jan", "Q-end": month/word labels without numbers are categories
    else:
        candidates = _DATE_FORMATS
    for fmt in candidates:
        try:
            pd.to_datetime(uniques, format=fmt)
        except (ValueError, TypeError):
            continue
        return fmt
    return None


def parse_date_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Turn text columns that hold dates into datetimes.

    CSV has no date type, and text dates also turn up in Excel files and in
    API data, so such columns would be plotted as category labels — and
    ``x_date_format`` (``%Y``, ``%b %y``) would have nothing to act on.

    A column is converted only when *every* non-empty value parses with one
    format: ISO (``2024-01-31``, ``2024-01``), numeric day/month/year
    (``31/01/2024``), or month names (``Jan 2024``, ``15 Jan 2024``,
    ``Jan-24``).  Numbers are never converted, and bare years (``"2021"``)
    stay as they are.
    """
    out = df.copy()
    for col in out.columns:
        s = out[col]
        if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
            continue
        text = s.dropna().astype(str).str.strip()
        if text.empty:
            continue
        fmt = _detect_date_format(text)
        if fmt is None:
            continue
        try:
            out[col] = pd.to_datetime(s.astype("string").str.strip(), format=fmt)
        except (ValueError, TypeError):
            continue
    return out


def load_mma_series(series_id: int) -> pd.DataFrame:
    """Fetch (or load from cache) one MMA series as a DataFrame (date columns detected)."""
    from .get_api_data import get_series_df  # noqa: PLC0415 — optional deps (requests)

    return parse_date_columns(get_series_df(int(series_id)))


def load_mma_info(series_id: int | str) -> dict:
    """Name, frequency and unit of one MMA series (``{}`` if unavailable)."""
    from .get_api_data import get_series_info  # noqa: PLC0415 — optional deps (requests)

    return get_series_info(int(series_id))
