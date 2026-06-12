"""Editorial y-axis limit and tick calculation (Economist/FT/Bloomberg style)."""

from __future__ import annotations

import math

NICE_FRACTIONS = (1, 2, 2.5, 5, 10)
_EPS = 1e-9


def _magnitude(x: float) -> float:
    """Return 10 ** floor(log10(x)) for x > 0."""
    return 10 ** math.floor(math.log10(x))


def _nice_candidates(raw_interval: float) -> list[float]:
    """Sorted nice interval candidates spanning a couple of magnitudes around raw_interval."""
    base_mag = _magnitude(raw_interval)
    candidates = set()
    for exp_offset in (-1, 0, 1, 2):
        mag = base_mag * (10 ** exp_offset)
        for f in NICE_FRACTIONS:
            candidates.add(round(f * mag, 12))
    return sorted(candidates)


def _floor_to_tick(value: float, interval: float) -> float:
    return math.floor(value / interval + _EPS) * interval


def _ceil_to_tick(value: float, interval: float) -> float:
    return math.ceil(value / interval - _EPS) * interval


def _approx_eq(a: float, b: float, interval: float) -> bool:
    return abs(a - b) <= _EPS * max(1.0, interval)


def _round_clean(value: float) -> float:
    return round(value, 10)


def calc_y_axis(
    data_min: float,
    data_max: float,
    chart_type: str,
    has_top_label: bool = False,
) -> dict:
    spans_zero = data_min < 0 < data_max
    raw_range = data_max - (0 if chart_type in ("bar", "area") else data_min)
    if raw_range <= 0:
        raw_range = abs(data_max) or 1.0

    best = None
    for interval in _nice_candidates(raw_range / 5):
        y_max = _ceil_to_tick(data_max, interval)
        if _approx_eq(y_max, data_max, interval):
            y_max += interval

        if chart_type in ("bar", "area"):
            y_min = 0.0
        elif spans_zero:
            y_min = -_ceil_to_tick(-data_min, interval)
        else:
            y_min_candidate = _floor_to_tick(data_min, interval)
            if _approx_eq(y_min_candidate, data_min, interval):
                y_min = y_min_candidate - interval
            else:
                y_min = y_min_candidate

            if y_min < 0 < y_max and data_min <= 0.4 * data_max:
                y_min = 0.0

        n_ticks = round((y_max - y_min) / interval) + 1
        candidate = (interval, y_min, y_max, n_ticks)

        if 4 <= n_ticks <= 6:
            best = candidate
            break

        if best is None or abs(n_ticks - 5) < abs(best[3] - 5):
            best = candidate

    interval, y_min, y_max, n_ticks = best

    if has_top_label:
        y_max += interval
        n_ticks += 1

    ticks = [_round_clean(y_min + i * interval) for i in range(n_ticks)]
    y_min = ticks[0]
    y_max = ticks[-1]

    return {
        "y_min": y_min,
        "y_max": y_max,
        "ticks": ticks,
        "tick_interval": _round_clean(interval),
        "zero_baseline": any(_approx_eq(t, 0.0, interval) for t in ticks),
    }
