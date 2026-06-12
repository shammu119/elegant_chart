# tests/test_compact_formatter.py
"""Unit tests for AxisMixin._compact_formatter (K/M/B suffixes and sub-1000 decimals)."""

from elegant_chart import ElegantChart


def _formatter(y_tick_interval=None):
    chart = ElegantChart()
    chart._y_tick_interval = y_tick_interval
    return lambda x: chart._compact_formatter(x, 0)


def test_thousands_suffix_strips_trailing_zero():
    fmt = _formatter()
    assert fmt(1000) == "1K"
    assert fmt(1500) == "1.5K"
    assert fmt(1100) == "1.1K"


def test_millions_and_billions_suffix_strips_trailing_zero():
    fmt = _formatter()
    assert fmt(1_000_000) == "1M"
    assert fmt(2_500_000) == "2.5M"
    assert fmt(1_000_000_000) == "1B"


def test_negative_large_values_keep_sign():
    fmt = _formatter()
    assert fmt(-1000) == "-1K"
    assert fmt(-2_500_000) == "-2.5M"


def test_sub_thousand_without_tick_interval_matches_legacy_integer_behavior():
    fmt = _formatter(y_tick_interval=None)
    assert fmt(500) == "500"
    assert fmt(0) == "0"


def test_sub_thousand_decimals_derive_from_tick_interval():
    fmt = _formatter(y_tick_interval=0.002)
    assert fmt(0.002) == "0.002"
    assert fmt(0.008) == "0.008"
    # Zero renders with the same precision as its sibling ticks, so the
    # axis reads as a consistent column of numbers.
    assert fmt(0.0) == "0.000"


def test_negative_zero_does_not_render_with_minus_sign():
    fmt = _formatter(y_tick_interval=None)
    assert fmt(-0.4) == "0"

    fmt_decimals = _formatter(y_tick_interval=0.002)
    assert fmt_decimals(-0.0001) == "0.000"


def test_half_unit_tick_interval_distinguishes_adjacent_ticks():
    # Regression: with 0 decimals, ticks at 0/0.5/1.0/1.5/2.0 collapsed to
    # "0"/"0"/"1"/"2"/"2" -- two indistinguishable pairs.
    fmt = _formatter(y_tick_interval=0.5)
    labels = [fmt(v) for v in (0, 0.5, 1.0, 1.5, 2.0)]
    assert labels == ["0.0", "0.5", "1.0", "1.5", "2.0"]
    assert len(set(labels)) == len(labels)
