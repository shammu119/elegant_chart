import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from PIL import Image  # noqa: E402

from elegant_chart import ChartSpec, ElegantChart, render  # noqa: E402
from elegant_chart.render import (  # noqa: E402
    SpecError,
    build_chart_kwargs,
    chart_data_xlsx_bytes,
    figure_png_bytes,
)


@pytest.fixture
def wide():
    return pd.DataFrame(
        {
            "Year": [2019, 2020, 2021, 2022, 2023],
            "EK": [10.0, 4.0, 7.0, 12.0, 15.0],
            "QR": [8.0, 3.0, 9.0, 10.0, 11.0],
            "UL": [5.0, 2.0, 4.0, 6.0, 7.0],
        }
    )


def _spec(ctype="bar"):
    spec = ChartSpec()
    spec.chart.type = ctype
    spec.chart.x_col = "Year"
    spec.chart.y_cols = ["EK", "QR"]
    spec.style.text.title = "Two-line\ntitle"
    spec.style.text.subtitle = "Passengers"
    spec.style.text.caption = "Source: test"
    return spec


@pytest.mark.parametrize("ctype", ["bar", "hbar", "line", "bump"])
def test_each_type_renders_canonical_size(wide, ctype):
    res = render(_spec(ctype), wide)
    try:
        img = Image.open(io.BytesIO(figure_png_bytes(res.fig, 500)))
        assert img.size == (1080, 1350)
    finally:
        res.close()


def test_switching_type_on_one_spec(wide):
    spec = _spec()
    for ctype in ("bar", "hbar", "line", "bump", "bar"):
        spec.chart.type = ctype
        render(spec, wide).close()
    assert spec.style.text.title == "Two-line\ntitle"


def test_render_matches_direct_library_call(wide):
    spec = _spec("line")
    spec.style.colors.theme = "consulting_light"
    spec.style.axes.y_tick_step = 5
    spec.chart.markers = True
    res = render(spec, wide)
    via_spec = figure_png_bytes(res.fig, 100)
    res.close()

    chart = ElegantChart(
        title="Two-line\ntitle",
        subtitle="Passengers",
        caption="Source: test",
        theme="consulting_light",
        y_tick_step=5,
    )
    fig, _ = chart.line(
        df=wide, x_col="Year", y_cols=["EK", "QR"], markers=True, show=False, export_xlsx=False
    )
    direct = figure_png_bytes(fig, 100)
    plt.close(fig)
    assert via_spec == direct


def test_stacked_hbar_and_options(wide):
    spec = _spec("bar")
    spec.chart.stacked = True
    spec.chart.show_value_labels = True
    spec.style.colors.color_map = {"EK": "secondary", "QR": "#FF0000"}
    spec.style.colors.alpha_map = {"QR": 0.5}
    spec.style.axes.y_formatter = "norm_max"
    spec.style.axes.y_formatter_decimals = 1
    spec.style.layout.logo_mode = "none"
    spec.style.text.annotations = [{"x": 2021, "y": 9, "text": "note", "arrow": True}]
    render(spec, wide).close()


def test_default_columns(wide):
    spec = ChartSpec()
    spec.chart.type = "line"
    res = render(spec, wide)
    assert [lbl for lbl, _ in res.chart._last_series_list] == ["EK", "QR", "UL"]
    res.close()


def test_missing_column_raises_spec_error(wide):
    spec = _spec()
    spec.chart.y_cols = ["Nope"]
    with pytest.raises(SpecError, match="Nope"):
        render(spec, wide)


def test_non_numeric_series_raises(wide):
    spec = _spec()
    spec.chart.y_cols = ["Year"]
    spec.chart.x_col = "EK"
    df = wide.assign(Year=wide["Year"].astype(str))
    with pytest.raises(SpecError, match="numeric"):
        render(spec, df)


def test_chart_data_xlsx_round_trip(wide):
    pytest.importorskip("openpyxl")
    res = render(_spec("bar"), wide)
    out = pd.read_excel(io.BytesIO(chart_data_xlsx_bytes(res.chart)))
    res.close()
    assert list(out.columns) == ["x", "EK", "QR"]
    assert out["EK"].tolist() == wide["EK"].tolist()


def test_logo_modes():
    spec = ChartSpec()
    assert build_chart_kwargs(spec)["logo_path"] is None
    spec.style.layout.logo_mode = "none"
    assert build_chart_kwargs(spec)["logo_path"] == ""
    spec.style.layout.logo_mode = "custom"
    spec.style.layout.logo_path = "/tmp/x.png"
    assert build_chart_kwargs(spec)["logo_path"] == "/tmp/x.png"


def test_annotations_resolve_text_x():
    from datetime import datetime

    from elegant_chart.render import resolve_annotations

    anns = [
        {"x": "2021", "y": "5", "text": "a"},
        {"x": "B", "y": 1, "text": "b", "arrow": 1},
        {"x": "1", "y": 1, "text": ""},
    ]
    assert resolve_annotations(anns[:1], [2020, 2021])[0]["x"] == 2021.0
    assert resolve_annotations(anns[1:], ["A", "B"]) == [
        {"x": 1.0, "y": 1.0, "text": "b", "arrow": True}
    ]
    dated = resolve_annotations(
        [{"x": "2021-01-01", "y": 1, "text": "d"}], [datetime(2020, 1, 1), datetime(2022, 1, 1)]
    )
    assert dated[0]["x"] > 18000  # matplotlib date number


def test_bump_ghost_and_label_options_are_passed_through(wide):
    from elegant_chart.render import build_call_kwargs

    spec = _spec("bump")
    spec.chart.highlight = ["EK"]
    spec.chart.other_color = "#FF00FF"
    spec.chart.other_alpha = 0.3
    spec.chart.hero_linewidth = 3.0
    spec.chart.other_linewidth = 0.5
    spec.chart.label_display = {"EK": "Emirates\nAirline", "QR": ""}
    method, kw = build_call_kwargs(spec, wide)
    assert method == "bump"
    assert kw["other_color"] == "#FF00FF" and kw["other_alpha"] == 0.3
    assert kw["hero_linewidth"] == 3.0 and kw["other_linewidth"] == 0.5
    assert kw["label_display"] == {"EK": "Emirates\nAirline"}
    render(spec, wide).close()


def test_concurrent_renders_do_not_mix_themes():
    """Two charts drawn at once must each keep their own theme (rcParams are global)."""
    import io
    import threading

    import pandas as pd
    from PIL import Image

    from elegant_chart.render import render_png_bytes
    from elegant_chart.spec import ChartSpec

    df = pd.DataFrame({"Year": pd.date_range("2012-01-01", periods=13, freq="YS"), "A": range(13)})
    results: list[tuple[str, tuple, tuple]] = []

    def work(theme: str) -> None:
        spec = ChartSpec()
        spec.chart.type, spec.chart.x_col, spec.chart.y_cols = "bar", "Year", ["A"]
        spec.style.colors.theme = theme
        spec.style.text.title = "Inflation"
        barrier.wait()
        for _ in range(12):
            im = Image.open(io.BytesIO(render_png_bytes(spec, df, 60))).convert("RGB")
            w, h = im.size
            results.append((theme, im.getpixel((3, 3)), im.getpixel((w // 2, int(h * 0.45)))))

    themes = ("newsroom_dark", "newsroom_muted", "consulting_light")
    barrier = threading.Barrier(len(themes))
    threads = [threading.Thread(target=work, args=(t,)) for t in themes]
    [t.start() for t in threads]
    [t.join() for t in threads]
    expect = {
        "newsroom_dark": (11, 16, 20),
        "newsroom_muted": (250, 250, 250),
        "consulting_light": (255, 255, 255),
    }
    assert len(results) == 36
    for theme, corner, middle in results:
        assert corner == expect[theme] == middle, (theme, corner, middle)


# ── half-filled axis ranges (one side "auto") ────────────────────────────────


def _limits(spec, df):
    res = render(spec, df)
    try:
        return res.ax.get_xlim(), res.ax.get_ylim()
    finally:
        res.close()


@pytest.mark.parametrize("ctype", ["bar", "line"])
def test_only_y_min_set_keeps_auto_max(wide, ctype):
    auto_x, auto_y = _limits(_spec(ctype), wide)
    spec = _spec(ctype)
    spec.style.axes.ylim = (-5.0, None)
    x, y = _limits(spec, wide)
    assert y[0] == pytest.approx(-5.0)
    assert y[1] == pytest.approx(auto_y[1])
    assert x == pytest.approx(auto_x)  # untouched axis is unchanged


@pytest.mark.parametrize("ctype", ["bar", "line"])
def test_only_y_max_set_keeps_auto_min(wide, ctype):
    _, auto_y = _limits(_spec(ctype), wide)
    spec = _spec(ctype)
    spec.style.axes.ylim = (None, 40.0)
    _, y = _limits(spec, wide)
    assert y[0] == pytest.approx(auto_y[0])
    assert y[1] == pytest.approx(40.0)


def test_only_x_max_set_keeps_auto_min(wide):
    auto_x, _ = _limits(_spec("line"), wide)
    spec = _spec("line")
    spec.style.axes.xlim = (None, 2030.0)
    x, _ = _limits(spec, wide)
    assert x[0] == pytest.approx(auto_x[0])
    assert x[1] == pytest.approx(2030.0)


def test_hbar_value_axis_half_range(wide):
    spec = _spec("hbar")
    spec.style.axes.ylim = (0.0, None)
    res = render(spec, wide)
    try:
        assert res.ax.get_xlim()[0] == pytest.approx(0.0)  # value axis is horizontal
    finally:
        res.close()


def test_half_range_survives_dict_round_trip(wide):
    spec = _spec("line")
    spec.style.axes.ylim = (0.0, None)
    again = ChartSpec.from_dict(spec.to_dict())
    assert again.style.axes.ylim == (0.0, None)
    assert _limits(again, wide)[1][0] == pytest.approx(0.0)


def test_half_range_does_not_mutate_the_spec(wide):
    spec = _spec("line")
    spec.style.axes.ylim = (0.0, None)
    render(spec, wide).close()
    assert spec.style.axes.ylim == (0.0, None)


def test_reversed_range_is_a_spec_error(wide):
    spec = _spec("line")
    spec.style.axes.ylim = (10.0, 5.0)
    with pytest.raises(SpecError, match="Y min"):
        render(spec, wide)
    spec.style.axes.ylim = (None, -50.0)  # auto min is above the typed max
    with pytest.raises(SpecError, match="Y min"):
        render(spec, wide)
