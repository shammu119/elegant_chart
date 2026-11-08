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
    """Parse uploaded CSV or Excel bytes into a DataFrame."""
    if is_excel(name):
        return pd.read_excel(io.BytesIO(data), sheet_name=sheet if sheet is not None else 0)
    if os.path.splitext(name or "")[1].lower() in (".csv", ".txt", ""):
        return pd.read_csv(io.BytesIO(data))
    raise ValueError(f"Unsupported file type: {name}. Use .csv or .xlsx.")


def load_mma_series(series_id: int) -> pd.DataFrame:
    """Fetch (or load from cache) one MMA series as a DataFrame."""
    from .get_api_data import get_series_df  # noqa: PLC0415 — optional deps (requests)

    return get_series_df(int(series_id))
