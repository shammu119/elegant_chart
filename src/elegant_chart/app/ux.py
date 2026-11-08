# elegant_chart/app/ux.py
"""Streamlit-free helpers behind Chart Studio's previews, checklist and theme cards.

Everything here is a pure function so it can be tested without a running app.
The previews mirror the formatters the chart really uses
(``AxisMixin._build_formatter``), so what the user sees is what they get.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Sequence

import pandas as pd

from elegant_chart.style_mixin import THEMES as _THEME_DEFS

# ── date labels ──────────────────────────────────────────────────────────────

DATE_PRESETS: tuple[tuple[str, str], ...] = (
    ("%Y", "Year"),
    ("%y", "Short year"),
    ("%b %Y", "Month and year"),
    ("%B %Y", "Full month and year"),
)
_KNOWN_CODES = set("YybBmdeaAjHMSIpUWwxXcZz%")
_MAX_SAMPLES = 6


@dataclass(frozen=True)
class DatePreview:
    labels: list[str]
    problem: Optional[str]


def sample_dates(values: Sequence[Any]) -> Optional[list[pd.Timestamp]]:
    """Up to six evenly spread dates from ``values`` (first and last always kept).

    Only real dates count: the chart applies a date format to date columns, not to
    whole numbers like 2019 or to category names.  Returns ``None`` otherwise, so
    callers hide the date controls instead of previewing something that won't happen.
    """
    vals = [v for v in list(values) if not pd.isna(v)]
    if not vals or not all(isinstance(v, datetime) for v in vals):
        return None
    dates = [pd.Timestamp(v) for v in vals]
    if len(dates) <= _MAX_SAMPLES:
        return dates
    last = len(dates) - 1
    idx = sorted({round(i * last / (_MAX_SAMPLES - 1)) for i in range(_MAX_SAMPLES)})
    return [dates[i] for i in idx]


def _is_yearly(dates: Sequence[pd.Timestamp]) -> bool:
    return (
        len(dates) > 1
        and len({(d.month, d.day) for d in dates}) == 1
        and len({d.year for d in dates}) == len(dates)
    )


def date_label_preview(code: str, dates: Sequence[pd.Timestamp]) -> DatePreview:
    """Labels ``code`` would print for ``dates``, plus a plain-language problem if any."""
    if not code or not code.strip():
        return DatePreview([], "Type a format such as %Y, or pick one above.")
    if re.search(r"%$", code):
        return DatePreview([], "The code ends with a lone %. Finish it, e.g. %Y.")
    for m in re.finditer(r"%(.)", code):
        if m.group(1) not in _KNOWN_CODES:
            return DatePreview([], f"{m.group(0)} is not a date code. Try %Y, %b or %m.")
    try:
        labels = [d.strftime(code) for d in dates]
    except ValueError:
        return DatePreview([], "That format could not be read.")
    spans_years = len({d.year for d in dates}) > 1
    has_year = bool(re.search(r"%[YyjUW]", code))
    has_month_day = bool(re.search(r"%[bBmdea]", code))
    if spans_years and not has_year:
        return DatePreview(labels, "This has no year, so labels repeat. Add %Y.")
    if _is_yearly(dates) and has_month_day:
        return DatePreview(
            labels, "Your data is yearly, so the month always prints Jan. Use %Y on its own."
        )
    return DatePreview(labels, None)


# ── value labels ─────────────────────────────────────────────────────────────


def _strip(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def value_style_problem(custom: str) -> Optional[str]:
    """``None`` if ``custom`` is a usable format string, else a plain-language message."""
    try:
        (custom or "").format(x=1.0)
    except (KeyError, IndexError, ValueError, AttributeError, TypeError):
        return "Can't read that format. Use a form like {x:,.1f}."
    return None


def format_value(
    style: str,
    x: float,
    decimals: int = 0,
    custom: str = "",
    max_value: Optional[float] = None,
) -> Optional[str]:
    """How ``x`` is printed in value ``style`` (a ``Y_FORMATTERS`` name).  ``None`` = bad custom."""
    if style == "plain":
        return f"{x:g}"
    if style == "percent":
        return f"{x * 100:g}%"
    if style == "norm_max":
        if not max_value:
            return ""
        out = f"{x / max_value:.{int(decimals)}f}"
        return out.rstrip("0").rstrip(".") if "." in out else out
    if style == "custom":
        if value_style_problem(custom):
            return None
        return custom.format(x=x)
    # compact (default)
    if abs(x) >= 1e9:
        return f"{_strip(x / 1e9)}B"
    if abs(x) >= 1e6:
        return f"{_strip(x / 1e6)}M"
    if abs(x) >= 1e3:
        return f"{_strip(x / 1e3)}K"
    return f"{x:.0f}" if float(x).is_integer() else f"{x:g}"


# ── progress checklist ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class ChecklistItem:
    key: str
    label: str
    state: str  # "done" | "next" | "optional" | "todo"
    hint: str


def checklist(*, has_data: bool, chart_ready: bool, has_title: bool) -> list[ChecklistItem]:
    """Five-step progress rail.  Exactly one step is ``next``."""
    done = [has_data, has_data and chart_ready, has_title]
    first_open = next(
        (i for i, d in enumerate(done) if not d), 3
    )  # 3 → everything required is done
    hints = [
        ("Load a series or a file to start.", "Data loaded"),
        ("Pick the x column and at least one series.", "Columns chosen"),
        ("Add a title so readers know what they see.", "Title set"),
    ]
    items: list[ChecklistItem] = []
    for i, (key, label) in enumerate([("data", "Data"), ("chart", "Chart"), ("titles", "Titles")]):
        if done[i]:
            state, hint = "done", hints[i][1]
        elif i == first_open:
            state, hint = "next", "Next: " + hints[i][0][0].lower() + hints[i][0][1:]
        else:
            state, hint = "todo", hints[i][0]
        items.append(ChecklistItem(key, label, state, hint))
    items.append(ChecklistItem("look", "Look", "optional", "Optional: colors, axes, footer."))
    if first_open == 3:
        items.append(ChecklistItem("export", "Export", "next", "Ready to export."))
    else:
        items.append(
            ChecklistItem("export", "Export", "todo", "Ready once the steps above are done.")
        )
    return items


def series_chip(info: Optional[dict], rows: int) -> Optional[str]:
    """One-line description of a fetched MMA series, or ``None`` without a name."""
    if not info or not info.get("name"):
        return None
    parts = [str(info["name"])]
    parts += [str(info[k]) for k in ("frequency", "unit") if info.get(k)]
    parts.append(f"{rows:,} rows")
    return " · ".join(parts)


# ── themes ───────────────────────────────────────────────────────────────────


def theme_palette(theme: str) -> tuple[str, ...]:
    return tuple(_THEME_DEFS[theme].palette)


def theme_bg(theme: str) -> str:
    return _THEME_DEFS[theme].bg_color


def theme_thumbnail_svg(theme: str, series: Sequence[Sequence[float]]) -> str:
    """Tiny line chart of the user's series in ``theme``'s colors (inline SVG)."""
    w, h, pad = 120, 64, 8
    pal = theme_palette(theme)
    out = [
        f'<svg viewBox="0 0 {w} {h}" width="100%" aria-hidden="true">'
        f'<rect width="{w}" height="{h}" rx="5" fill="{theme_bg(theme)}"/>'
    ]
    flat = [float(v) for s in series for v in s if not pd.isna(v)]
    top = max(flat) if flat else 0.0
    bottom = min(0.0, min(flat)) if flat else 0.0
    span = (top - bottom) or 1.0
    for i, s in enumerate(series):
        vals = [float(v) for v in s]
        if len(vals) < 2:
            continue
        pts = " ".join(
            f"{pad + j * (w - 2 * pad) / (len(vals) - 1):.1f},"
            f"{h - pad - (0 if pd.isna(v) else (v - bottom) / span) * (h - 2 * pad):.1f}"
            for j, v in enumerate(vals)
        )
        out.append(
            f'<polyline points="{pts}" fill="none" stroke="{pal[i % len(pal)]}" '
            'stroke-width="1.8" stroke-linejoin="round"/>'
        )
    out.append("</svg>")
    return "".join(out)
