from elegant_chart.spec import ChartSpec, StepSpec


def test_defaults_construct():
    spec = ChartSpec()
    assert spec.chart.type == "bar"
    assert spec.style.colors.theme == "newsroom_dark"
    assert spec.style.layout.align_x_edges is True
    assert spec.steps == []


def test_round_trip_preserves_everything():
    spec = ChartSpec()
    spec.source.kind = "mma"
    spec.source.series_id = 101
    spec.steps = [
        StepSpec("filter", {"column": "Type", "operator": "=", "value": "International"}),
        StepSpec("top_n", {"n": 10}),
    ]
    spec.chart.type = "hbar"
    spec.chart.x_col = "Airline"
    spec.chart.y_cols = ["Total Passengers"]
    spec.chart.logos = {"Emirates": "/tmp/ek.png"}
    spec.style.text.title = "Line one\nLine two"
    spec.style.text.annotations = [{"x": 1, "y": 2, "text": "hi", "arrow": True}]
    spec.style.axes.xlim = (0.0, 10.0)
    spec.style.colors.color_map = {"Total Passengers": "#64D2FF"}
    spec.style.legend.legend_ncol = 2

    again = ChartSpec.from_dict(spec.to_dict())
    assert again == spec
    assert isinstance(again.style.axes.xlim, tuple)


def test_from_dict_ignores_unknown_keys():
    spec = ChartSpec.from_dict({"chart": {"type": "line", "bogus": 1}, "extra": {}})
    assert spec.chart.type == "line"


def test_switching_type_keeps_style():
    spec = ChartSpec()
    spec.style.text.title = "Keep me"
    spec.style.axes.y_tick_step = 5
    for t in ("hbar", "line", "bump", "bar"):
        spec.chart.type = t
        assert spec.style.text.title == "Keep me"
        assert spec.style.axes.y_tick_step == 5
