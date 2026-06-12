import math

from elegant_chart.axis_utils import calc_y_axis


def _assert_evenly_spaced(result):
    ticks = result["ticks"]
    interval = result["tick_interval"]
    assert ticks[0] == result["y_min"]
    assert ticks[-1] == result["y_max"]
    for a, b in zip(ticks, ticks[1:]):
        assert math.isclose(b - a, interval, rel_tol=1e-9, abs_tol=1e-9)


def test_bar_zero_to_eighty_three():
    result = calc_y_axis(0, 83, "bar")
    assert result["y_min"] == 0
    assert result["y_max"] > 83
    assert result["y_max"] in (90, 100)
    assert 4 <= len(result["ticks"]) <= 6
    assert result["zero_baseline"] is True
    _assert_evenly_spaced(result)


def test_line_zero_to_eighty_three_matches_bar():
    bar_result = calc_y_axis(0, 83, "bar")
    line_result = calc_y_axis(0, 83, "line")
    assert line_result["y_min"] == bar_result["y_min"] == 0
    assert line_result["y_max"] == bar_result["y_max"]
    assert 4 <= len(line_result["ticks"]) <= 6
    _assert_evenly_spaced(line_result)


def test_line_forty_two_to_eighty_three_floats_axis():
    result = calc_y_axis(42, 83, "line")
    assert result["y_min"] != 0
    assert 30 <= result["y_min"] <= 42
    assert result["y_max"] > 83
    assert 4 <= len(result["ticks"]) <= 6
    _assert_evenly_spaced(result)


def test_line_eight_twenty_to_ten_fifty():
    # Note: the 4-6 tick target (rule 1) takes priority over the illustrative
    # interval-of-50 example, so this resolves to interval=100 (4 ticks)
    # rather than interval=50 (7 ticks).
    result = calc_y_axis(820, 1050, "line")
    assert result["y_min"] <= 820
    assert result["y_max"] > 1050
    assert 4 <= len(result["ticks"]) <= 6
    _assert_evenly_spaced(result)


def test_line_negative_to_positive_includes_zero():
    result = calc_y_axis(-3.2, 7.6, "line")
    assert 0.0 in result["ticks"]
    assert result["zero_baseline"] is True
    assert result["y_min"] <= -3.2
    assert result["y_max"] > 7.6
    assert 4 <= len(result["ticks"]) <= 6
    _assert_evenly_spaced(result)


def test_line_small_decimals():
    result = calc_y_axis(0.002, 0.0087, "line")
    assert result["y_min"] == 0
    assert result["zero_baseline"] is True
    assert result["y_max"] > 0.0087
    assert 4 <= len(result["ticks"]) <= 6
    _assert_evenly_spaced(result)


def test_has_top_label_extends_y_max_by_one_interval():
    base = calc_y_axis(0, 83, "line")
    with_label = calc_y_axis(0, 83, "line", has_top_label=True)
    assert with_label["tick_interval"] == base["tick_interval"]
    assert with_label["y_max"] == base["y_max"] + base["tick_interval"]
    assert len(with_label["ticks"]) == len(base["ticks"]) + 1
    _assert_evenly_spaced(with_label)


def test_touch_avoidance_bumps_y_max():
    result = calc_y_axis(0, 100, "bar")
    assert result["y_max"] > 100
    _assert_evenly_spaced(result)
