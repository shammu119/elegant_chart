"""Smoke tests for the Chart Studio Streamlit script (skipped without Streamlit)."""

from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from elegant_chart.spec import StepSpec  # noqa: E402

STUDIO = str(Path(__file__).resolve().parents[1] / "src" / "elegant_chart" / "app" / "studio.py")


def _app_with_data():
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    at.session_state.raw_df = pd.DataFrame(
        {
            "Airline": ["Emirates", "Qatar Airways", "IndiGo", "Emirates", "Gulf Air"],
            "Type": ["International"] * 4 + ["Domestic"],
            "Total Passengers": [100.0, 80.0, 60.0, 50.0, 10.0],
        }
    )
    at.session_state.raw_key = "test"
    return at


def test_empty_session_runs():
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    assert not at.exception
    assert any("Load data" in i.value for i in at.info)


def test_airline_flow_builds_preview_and_type_switch_keeps_title():
    at = _app_with_data()
    spec = at.session_state.spec
    spec.steps = [
        StepSpec("filter", {"column": "Type", "operator": "=", "value": "International"}),
        StepSpec("group", {"by": ["Airline"], "agg": "sum", "columns": ["Total Passengers"]}),
        StepSpec("sort", {"column": "Total Passengers", "ascending": False}),
        StepSpec("top_n", {"n": 10}),
    ]
    at.session_state.step_ids = ["a", "b", "c", "d"]
    at.run()
    assert not at.exception, at.exception
    assert not at.error, [e.value for e in at.error]

    at.text_area(key="text.title").input("Maldives Gateway:\nMost Popular Airlines")
    at.radio(key="chart.type").set_value("hbar")
    at.run()
    assert not at.exception
    assert not at.error, [e.value for e in at.error]
    assert at.session_state.spec.chart.type == "hbar"
    assert at.session_state.spec.chart.x_col == "Airline"
    assert at.session_state.spec.chart.y_cols == ["Total Passengers"]
    assert len(at.get("image")) == 1

    for ctype in ("line", "bar"):
        at.radio(key="chart.type").set_value(ctype)
        at.run()
        assert not at.exception
        assert at.session_state.spec.style.text.title == "Maldives Gateway:\nMost Popular Airlines"


def test_failing_step_is_shown_inline():
    at = _app_with_data()
    at.session_state.spec.steps = [
        StepSpec("sort", {"column": "Gone", "ascending": True}),
        StepSpec("top_n", {"n": 2}),
    ]
    at.session_state.step_ids = ["x", "y"]
    at.run()
    assert not at.exception
    assert any("Gone" in e.value for e in at.error)
