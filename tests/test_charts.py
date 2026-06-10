# tests/test_charts.py
"""
Headless smoke tests for ElegantChart.

Uses the Agg (non-interactive) backend so tests run without a display.
All chart calls use show=False so plt.show() is never triggered.
"""

import os
import pytest
import matplotlib

matplotlib.use("Agg")  # must be set before importing pyplot

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime

from elegant_chart import ElegantChart


# ── helpers ───────────────────────────────────────────────────────────────────


def make_chart(**kwargs) -> ElegantChart:
    return ElegantChart(**{"title": "Test", **kwargs})


def assert_figure(result):
    fig, ax = result
    assert isinstance(fig, plt.Figure)
    assert isinstance(ax, plt.Axes)
    plt.close(fig)


THEMES = ["consulting_light", "newsroom_muted", "consulting_dark", "newsroom_dark"]


# ── import / instantiation smoke ──────────────────────────────────────────────


def test_import():
    from elegant_chart import ElegantChart, ChartBase, XPlan, YFormatter

    assert ElegantChart is not None


def test_instantiation_defaults():
    c = ElegantChart()
    assert c.theme == "newsroom_dark"
    assert c.dpi == 150
    assert c.figsize == (2.16, 2.70), "Default figsize must yield 1080×1350 px at save_dpi=500"
    assert c._figure_scale == pytest.approx(0.6), "_figure_scale must be 0.6 at the default figsize (2.16/3.6)"
    assert c.font_scale == 0.9
    assert isinstance(c.palette, list)
    assert all(isinstance(color, str) for color in c.palette), (
        "All palette entries must be plain hex strings"
    )


def test_default_line_style_is_compact():
    c = make_chart()
    fig, ax = c.line(x=[1, 2, 3], ys=[1, 2, 3], show=False)
    line = ax.lines[0]
    assert line.get_linewidth() == pytest.approx(c._px(0.6))
    assert line.get_marker() == "None"
    plt.close(fig)


def test_instantiation_all_themes():
    for theme in THEMES:
        c = ElegantChart(theme=theme)
        assert isinstance(c.palette, list), f"{theme}: palette must be a list"
        assert all(isinstance(p, str) for p in c.palette), (
            f"{theme}: palette must contain only strings, not tuples"
        )


# ── bar chart — x types ───────────────────────────────────────────────────────


def test_bar_categorical():
    c = make_chart()
    assert_figure(c.bar(x=["A", "B", "C"], ys=[1, 2, 3], show=False))


def test_bar_numeric():
    c = make_chart()
    assert_figure(c.bar(x=[1, 2, 3, 4], ys=[10, 20, 15, 25], show=False))


def test_bar_datetime():
    c = make_chart()
    dates = [datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2022, 1, 1)]
    assert_figure(c.bar(x=dates, ys=[100, 120, 110], show=False))


# ── bar chart — modes ─────────────────────────────────────────────────────────


def test_bar_multi_grouped():
    c = make_chart()
    assert_figure(
        c.bar(
            x=["Q1", "Q2", "Q3"],
            ys=[[10, 20, 15], [5, 12, 8]],
            labels=["A", "B"],
            show=False,
        )
    )


def test_bar_stacked():
    c = make_chart()
    assert_figure(
        c.bar(
            x=["Q1", "Q2", "Q3"],
            ys=[[10, 20, 15], [5, 12, 8]],
            labels=["A", "B"],
            stacked=True,
            show=False,
        )
    )


def test_bar_dict_ys():
    c = make_chart()
    assert_figure(c.bar(x=["X", "Y", "Z"], ys={"Series": [1, 2, 3]}, show=False))


# ── bar chart — all themes ────────────────────────────────────────────────────


@pytest.mark.parametrize("theme", THEMES)
def test_bar_all_themes(theme):
    c = make_chart(theme=theme)
    assert_figure(c.bar(x=["A", "B", "C"], ys=[1, 2, 3], show=False))


# ── line chart — x types ──────────────────────────────────────────────────────


def test_line_categorical():
    c = make_chart()
    assert_figure(c.line(x=["Jan", "Feb", "Mar"], ys=[10, 12, 9], show=False))


def test_line_numeric():
    c = make_chart()
    assert_figure(c.line(x=[0, 1, 2, 3], ys=[0, 1, 4, 9], show=False))


def test_line_datetime():
    c = make_chart()
    dates = [datetime(2020, 1, 1), datetime(2021, 6, 1), datetime(2022, 12, 1)]
    assert_figure(c.line(x=dates, ys=[5, 7, 6], show=False))


# ── line chart — multi-series + markers ──────────────────────────────────────


def test_line_multi_series():
    c = make_chart()
    assert_figure(
        c.line(
            x=["A", "B", "C", "D"],
            ys=[[1, 2, 3, 4], [4, 3, 2, 1]],
            labels=["Up", "Down"],
            show=False,
        )
    )


def test_line_no_markers():
    c = make_chart()
    assert_figure(c.line(x=[1, 2, 3], ys=[1, 4, 2], markers=False, show=False))


@pytest.mark.parametrize("theme", THEMES)
def test_line_all_themes(theme):
    c = make_chart(theme=theme)
    assert_figure(c.line(x=["A", "B", "C"], ys=[3, 1, 2], show=False))


# ── DataFrame path ────────────────────────────────────────────────────────────


def test_bar_from_dataframe():
    df = pd.DataFrame({"month": ["Jan", "Feb", "Mar"], "sales": [100, 120, 90]})
    c = make_chart()
    assert_figure(c.bar(df=df, x_col="month", y_cols="sales", show=False))


def test_line_from_dataframe():
    df = pd.DataFrame({"x": [1, 2, 3, 4], "y1": [1, 4, 9, 16], "y2": [2, 3, 4, 5]})
    c = make_chart()
    assert_figure(c.line(df=df, x_col="x", y_cols=["y1", "y2"], show=False))


def test_get_series_df_uses_cached_excel(tmp_path, monkeypatch):
    pytest.importorskip("openpyxl")
    monkeypatch.chdir(tmp_path)

    expected = pd.DataFrame({"x": ["A", "B"], "y": [1, 2]})
    cache_file = tmp_path / "data" / "series_2307.xlsx"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    expected.to_excel(cache_file, index=False, engine="openpyxl")

    from elegant_chart.get_api_data import get_series_df

    result = get_series_df(2307)
    pd.testing.assert_frame_equal(result, expected)


def test_get_series_df_creates_excel_cache_on_api_fetch(tmp_path, monkeypatch):
    requests = pytest.importorskip("requests")
    pytest.importorskip("openpyxl")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MMA_API_TOKEN", "fake-token")

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": [
                    {
                        "data": [
                            {"x": "A", "y": 1},
                            {"x": "B", "y": 2},
                        ]
                    }
                ]
            }

    def fake_get(url, auth, verify, timeout):
        assert "database.mma.gov.mv" in url
        return DummyResponse()

    monkeypatch.setattr(requests, "get", fake_get)

    from elegant_chart.get_api_data import get_series_df

    result = get_series_df(2307)
    expected = pd.DataFrame([{"x": "A", "y": 1}, {"x": "B", "y": 2}])
    pd.testing.assert_frame_equal(result, expected)

    cached_file = tmp_path / "data" / "series_2307.xlsx"
    assert cached_file.exists()
    loaded = pd.read_excel(cached_file, engine="openpyxl")
    pd.testing.assert_frame_equal(loaded, expected)


# ── save_path round-trip ──────────────────────────────────────────────────────


def test_bar_save(tmp_path):
    out = tmp_path / "chart.png"
    c = make_chart()
    c.bar(x=["A", "B", "C"], ys=[1, 2, 3], show=False, save_path=str(out))
    assert out.exists() and out.stat().st_size > 0


def test_line_save(tmp_path):
    out = tmp_path / "line.png"
    c = make_chart()
    c.line(x=[1, 2, 3], ys=[1, 2, 1], show=False, save_path=str(out))
    assert out.exists() and out.stat().st_size > 0


# ── configurable DPI ──────────────────────────────────────────────────────────


def test_custom_dpi():
    c = ElegantChart(dpi=72)
    assert c._rc["figure.dpi"] == 72


# ── figure scale proportionality ─────────────────────────────────────────────


def test_figure_scale_proportional():
    """At 2× the reference figsize, _figure_scale == 2.0 and helpers scale accordingly."""
    c = ElegantChart(figsize=(7.2, 9.0))  # exactly 2× (3.6, 4.5)
    assert c._figure_scale == 2.0
    # _fs multiplies base × font_scale and caps figure enlargement at 1.0.
    assert c._fs(10) == pytest.approx(10 * c.font_scale * min(c._figure_scale, 1.0))
    # _px multiplies base × _figure_scale only
    assert c._px(1.0) == 2.0


# ── compact_years opt-in ──────────────────────────────────────────────────────


def test_compact_years_disabled_preserves_integers():
    """Integer-like labels must not be mangled when compact_years=False (default)."""
    c = make_chart()
    # If compact_years were always on, [1001, 1002, 1003] → ["1001", "2", "3"]
    fig, ax = c.bar(
        x=["1001", "1002", "1003"],
        ys=[10, 20, 30],
        compact_years=False,
        show=False,
    )
    tick_labels = [t.get_text() for t in ax.get_xticklabels()]
    assert "1001" in tick_labels
    # Second label must NOT be "2"
    assert "2" not in tick_labels
    plt.close(fig)


def test_compact_years_enabled():
    """When opted in, year-like labels are abbreviated after the first."""
    from elegant_chart.data_mixin import DataMixin

    result = DataMixin._compact_years(["2020", "2021", "2022"], enabled=True)
    assert result == ["2020", "21", "22"]


def test_compact_years_disabled():
    from elegant_chart.data_mixin import DataMixin

    result = DataMixin._compact_years(["2020", "2021", "2022"], enabled=False)
    assert result == ["2020", "2021", "2022"]


# ── error cases ───────────────────────────────────────────────────────────────


def test_error_empty_x():
    c = make_chart()
    with pytest.raises(ValueError, match="empty"):
        c.bar(x=[], ys=[], show=False)


def test_error_length_mismatch():
    c = make_chart()
    with pytest.raises(ValueError, match="length"):
        c.bar(x=["A", "B", "C"], ys=[1, 2], show=False)


def test_error_non_finite():
    c = make_chart()
    with pytest.raises(ValueError, match="non-finite"):
        c.bar(x=["A", "B"], ys=[1, float("nan")], show=False)


def test_error_no_ys():
    c = make_chart()
    with pytest.raises(ValueError):
        c.bar(x=["A", "B"], show=False)


def test_error_df_missing_cols():
    df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    c = make_chart()
    with pytest.raises(ValueError):
        c.bar(x=None, df=df, show=False)


# ── font warning ─────────────────────────────────────────────────────────────


def test_sf_pro_missing_emits_warning():
    """UserWarning must be raised when SF Pro is absent (true on any standard CI/dev box)."""
    from matplotlib import font_manager

    available = {f.name for f in font_manager.fontManager.ttflist}
    if "SF Pro" in available or "SF Pro Text" in available or "SF Pro Display" in available:
        pytest.skip("SF Pro is installed on this machine — fallback path not exercised")

    with pytest.warns(UserWarning, match="SF Pro fonts not found"):
        ElegantChart()


# ── export_data ───────────────────────────────────────────────────────────────


def test_export_data_bar(tmp_path):
    out = tmp_path / "export.xlsx"
    c = make_chart()
    c.bar(x=["A", "B", "C"], ys=[1, 2, 3], show=False)
    c.export_data(str(out))

    assert out.exists() and out.stat().st_size > 0
    df = pd.read_excel(out)
    assert list(df.columns) == ["x", "value"]
    assert list(df["x"]) == ["A", "B", "C"]
    assert list(df["value"]) == [1, 2, 3]


def test_export_data_line_multi_series(tmp_path):
    out = tmp_path / "export.xlsx"
    c = make_chart()
    c.line(
        x=["Jan", "Feb", "Mar"],
        ys=[[10, 20, 30], [5, 15, 25]],
        labels=["Revenue", "Cost"],
        show=False,
    )
    c.export_data(str(out))

    df = pd.read_excel(out)
    assert set(df.columns) == {"x", "Revenue", "Cost"}
    assert list(df["Revenue"]) == [10, 20, 30]
    assert list(df["Cost"]) == [5, 15, 25]


def test_export_data_overwrites_on_second_render(tmp_path):
    out = tmp_path / "export.xlsx"
    c = make_chart()
    c.bar(x=["A"], ys=[1], show=False)
    c.line(x=["X", "Y"], ys=[9, 8], show=False)  # second render
    c.export_data(str(out))

    df = pd.read_excel(out)
    assert list(df["x"]) == ["X", "Y"], "export_data should reflect the most recent render"


def test_export_data_before_render_raises():
    c = make_chart()
    with pytest.raises(RuntimeError, match="Call bar\\(\\) or line\\(\\)"):
        c.export_data("should_not_exist.xlsx")


# ── value labels (optional, off by default) ──────────────────────────────────


def test_bar_value_labels_off_by_default():
    """show_value_labels=True must add more text objects than the default (off)."""
    c1 = make_chart()
    _, ax1 = c1.bar(x=["A", "B", "C"], ys=[10, 20, 30], show=False)
    texts_off = len(ax1.texts)
    plt.close()

    c2 = make_chart()
    _, ax2 = c2.bar(x=["A", "B", "C"], ys=[10, 20, 30], show_value_labels=True, show=False)
    texts_on = len(ax2.texts)
    plt.close()

    assert texts_on > texts_off, "show_value_labels=True must add value-label text objects"


def test_bar_value_labels_on():
    c = make_chart()
    fig, ax = c.bar(x=["A", "B", "C"], ys=[10, 20, 30], show_value_labels=True, show=False)
    label_texts = [t.get_text() for t in ax.texts]
    assert "10" in label_texts
    assert "20" in label_texts
    assert "30" in label_texts
    plt.close(fig)


def test_line_value_labels_on():
    c = make_chart()
    fig, ax = c.line(
        x=["Jan", "Feb", "Mar"], ys=[100, 200, 150], show_value_labels=True, show=False
    )
    label_texts = [t.get_text() for t in ax.texts]
    assert "100" in label_texts
    assert "200" in label_texts
    assert "150" in label_texts
    plt.close(fig)


# ── auto bar width ────────────────────────────────────────────────────────────


def test_auto_bar_width_categorical_sparse():
    """Sparse categorical data should produce narrower bars than dense data."""
    from elegant_chart.data_mixin import DataMixin, XPlan
    import numpy as np

    dm = DataMixin()
    plan_sparse = XPlan(True, False, False, np.arange(3, dtype=float), False, None)
    plan_dense = XPlan(True, False, False, np.arange(20, dtype=float), False, None)
    assert dm._auto_bar_width(plan_sparse, 3) < dm._auto_bar_width(plan_dense, 20)


def test_auto_bar_width_datetime_scales_with_gap():
    """Datetime positions: width should be proportional to the minimum gap."""
    from elegant_chart.data_mixin import DataMixin, XPlan
    import numpy as np

    dm = DataMixin()
    # Tight series: gap=1
    plan_tight = XPlan(False, True, False, np.array([0.0, 1.0, 2.0]), False, None)
    # Sparse series: gap=365
    plan_loose = XPlan(False, True, False, np.array([0.0, 365.0, 730.0]), False, None)
    assert dm._auto_bar_width(plan_loose, 3) > dm._auto_bar_width(plan_tight, 3)


def test_bar_explicit_width_respected():
    """An explicit bar_width= overrides auto-sizing."""
    c = make_chart()
    fig, ax = c.bar(x=["A", "B"], ys=[1, 2], bar_width=0.3, show=False)
    rects = [p for p in ax.patches]
    assert all(abs(p.get_width() - 0.3) < 0.01 for p in rects), "Explicit width should be used"
    plt.close(fig)


# ── economist y-tick labels inside plot ───────────────────────────────────────


def test_economist_ytick_labels_are_inside_axes():
    """Y-tick labels must be rendered as ax.texts (inside), not as yticklabels."""
    c = make_chart()
    fig, ax = c.bar(x=["A", "B", "C"], ys=[1000, 2000, 3000], show=False)
    # Default yticklabels should be empty (labels hidden, drawn as ax.texts instead)
    visible_ytick_labels = [t.get_text() for t in ax.get_yticklabels() if t.get_visible()]
    assert all(lbl == "" for lbl in visible_ytick_labels), (
        "Default yticklabels should be hidden; labels go inside via ax.text()"
    )
    # At least one inside text label should exist
    assert any(t.get_text() for t in ax.texts), "Expected economist-style inside tick labels"
    plt.close(fig)


# ── palette shape (no tuples) ─────────────────────────────────────────────────


@pytest.mark.parametrize("theme", THEMES)
def test_palette_is_flat_strings(theme):
    c = ElegantChart(theme=theme)
    for entry in c.palette:
        assert isinstance(entry, str), (
            f"Theme '{theme}' palette contains a non-string entry: {entry!r}"
        )


# ── legend visibility (single vs. multi series) ───────────────────────────


def test_single_labeled_series_suppresses_legend():
    """A lone labelled series relies on the subtitle; no legend is drawn."""
    c = make_chart()
    fig, ax = c.bar(x=["A", "B", "C"], ys={"Occupancy": [1, 2, 3]}, show=False)
    assert ax.get_legend() is None
    plt.close(fig)


def test_unlabeled_single_series_has_no_legend():
    c = make_chart()
    fig, ax = c.line(x=["A", "B", "C"], ys=[1, 2, 3], show=False)
    assert ax.get_legend() is None
    plt.close(fig)


def test_multi_series_legend_uses_multi_column_grid():
    """>=2 labelled series draw a legend arranged as a 2-3 column grid."""
    c = make_chart()
    fig, ax = c.line(
        x=["A", "B", "C"],
        ys=[[1, 2, 3], [3, 2, 1]],
        labels=["Up", "Down"],
        show=False,
    )
    legend = ax.get_legend()
    assert legend is not None
    # Attribute was renamed _ncol -> _ncols in matplotlib 3.6.
    ncols = getattr(legend, "_ncols", None) or getattr(legend, "_ncol", 1)
    assert ncols == 2
    plt.close(fig)


# ── x-axis boundary ticks ──────────────────────────────────────────────────


def test_boundary_ticks_drawn_at_xlim():
    """_finalize_axes adds short vertical Line2D segments at both x-limits."""
    c = make_chart()
    fig, ax = c.line(x=[0, 1, 2, 3], ys=[0, 1, 4, 9], show=False)
    xlim = ax.get_xlim()

    # Boundary ticks are the only Line2D segments with two equal x-values.
    boundary_x = {
        ln.get_xdata()[0]
        for ln in ax.lines
        if len(ln.get_xdata()) == 2 and ln.get_xdata()[0] == ln.get_xdata()[1]
    }
    assert set(xlim) <= boundary_x, "Expected a boundary tick at both xlim endpoints"
    plt.close(fig)


def test_boundary_ticks_present_for_datetime_axis():
    """Boundary ticks also anchor datetime axes, where AutoDateLocator may
    skip the exact endpoints."""
    c = make_chart()
    dates = [datetime(2020, 1, 1), datetime(2021, 6, 1), datetime(2022, 12, 1)]
    fig, ax = c.line(x=dates, ys=[5, 7, 6], show=False)
    xlim = ax.get_xlim()

    boundary_x = {
        ln.get_xdata()[0]
        for ln in ax.lines
        if len(ln.get_xdata()) == 2 and ln.get_xdata()[0] == ln.get_xdata()[1]
    }
    assert set(xlim) <= boundary_x
    plt.close(fig)


# ── color roles & color_map ────────────────────────────────────────────────


def test_series_color_is_positional_by_default():
    """Unconfigured series take colors by order via the named role table."""
    c = make_chart()
    assert c._series_color(0) == c.color_roles["primary"] == c.palette[0]
    assert c._series_color(1) == c.color_roles["secondary"] == c.palette[1]


def test_series_color_map_role_override():
    """color_map may pin a labelled series to a named role out of order."""
    c = make_chart(color_map={"Resorts": "tertiary"})
    assert c._series_color(0, "Resorts") == c.color_roles["tertiary"]
    # An unmapped label still falls back to its positional role.
    assert c._series_color(1, "Hotels") == c.color_roles["secondary"]


def test_series_color_map_hex_override():
    """color_map may also pin a labelled series to a literal hex color."""
    c = make_chart(color_map={"Hotels": "#ABCDEF"})
    assert c._series_color(1, "Hotels") == "#ABCDEF"


def test_bar_series_colors_follow_role_table():
    """Rendered grouped-bar colors match _series_color's role-based assignment.

    Each series is drawn via its own ax.bar() call (bar_mixin's grouped-bar
    loop), so ax.patches holds series A's 2 bars first, then series B's —
    individual Rectangle patches all get label='_nolegend_' in matplotlib,
    so position (not get_label()) is what identifies each series here.
    """
    from matplotlib.colors import to_hex

    c = make_chart()
    fig, ax = c.bar(
        x=["Q1", "Q2"],
        ys=[[1, 2], [3, 4]],
        labels=["A", "B"],
        show=False,
    )
    assert len(ax.patches) == 4
    expected_a = c._series_color(0, "A").lower()
    expected_b = c._series_color(1, "B").lower()
    assert to_hex(ax.patches[0].get_facecolor()) == expected_a
    assert to_hex(ax.patches[1].get_facecolor()) == expected_a
    assert to_hex(ax.patches[2].get_facecolor()) == expected_b
    assert to_hex(ax.patches[3].get_facecolor()) == expected_b
    plt.close(fig)
