# elegant_chart/get_api_data.py
"""
Optional data-loading helper for the MMA Statistics API.

Authentication
--------------
The bearer token is resolved in this order:

1. Environment variable ``MMA_API_TOKEN``
2. A local file ``TOKEN.txt`` (never committed — listed in .gitignore)

If neither exists, :func:`get_series_df` raises ``RuntimeError`` with instructions.

Usage
-----
::

    from elegant_chart.get_api_data import get_series_df

    df = get_series_df(2307)          # fetches series id 2307
    df.to_excel("data.xlsx", index=False)

Requires the ``data`` optional dependency group::

    pip install "elegant_chart[data]"
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

CACHE_DIR = Path("data")


def _load_token() -> str:
    """Return the MMA API bearer token, or raise RuntimeError."""
    token = os.environ.get("MMA_API_TOKEN")
    if token:
        return token

    token_file = Path("TOKEN.txt")
    if token_file.exists():
        text = token_file.read_text().strip()
        if text:
            return text

    raise RuntimeError(
        "MMA API token not found. Set the MMA_API_TOKEN environment variable, "
        "or create a TOKEN.txt file in the working directory containing only the token. "
        "TOKEN.txt is gitignored — do not commit it."
    )


def _series_cache_path(series_id: int) -> Path:
    return CACHE_DIR / f"series_{series_id}.xlsx"


def _load_cached_series_df(path: Path) -> pd.DataFrame:
    try:
        import openpyxl  # noqa: PLC0415 — optional dependency, imported lazily
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required to read cached Excel data. "
            "Install it with: pip install \"elegant_chart[data]\""
        ) from exc

    return pd.read_excel(path, engine="openpyxl")


def _save_cached_series_df(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import openpyxl  # noqa: PLC0415 — optional dependency, imported lazily
    except ImportError as exc:
        raise ImportError(
            "openpyxl is required to cache API data as Excel. "
            "Install it with: pip install \"elegant_chart[data]\""
        ) from exc

    df.to_excel(path, index=False, engine="openpyxl")


def get_series_df(series_id: int, timeout: int = 30) -> pd.DataFrame:
    """
    Fetch a single time series from the MMA Statistics database.

    If a cached Excel file exists at ``data/series_<id>.xlsx``, it is loaded
    instead of calling the API. When the file is missing, the API is fetched
    and the result is saved to the cache folder.

    Parameters
    ----------
    series_id:
        The numeric series identifier from ``database.mma.gov.mv``.
    timeout:
        Request timeout in seconds (default 30).

    Returns
    -------
    pandas.DataFrame
        A DataFrame of the series ``data`` records, or an empty DataFrame if
        the series was not found.
    """
    cached_path = _series_cache_path(series_id)
    if cached_path.exists():
        return _load_cached_series_df(cached_path)

    try:
        import requests  # noqa: PLC0415 — optional dependency, imported lazily
    except ImportError as exc:
        raise ImportError(
            "The 'requests' package is required to use get_series_df. "
            "Install it with: pip install \"elegant_chart[data]\""
        ) from exc

    token = _load_token()

    def _bearer(r: "requests.PreparedRequest") -> "requests.PreparedRequest":
        r.headers["Authorization"] = f"Bearer {token}"
        return r

    url = f"https://database.mma.gov.mv/api/series?ids={series_id}"
    response = requests.get(url, auth=_bearer, verify=True, timeout=timeout)
    response.raise_for_status()

    json_data = response.json()
    series_list = json_data.get("data", [])
    if not series_list:
        return pd.DataFrame()

    series = series_list[0]
    df = pd.DataFrame(series.get("data", []))
    _save_cached_series_df(cached_path, df)
    return df
