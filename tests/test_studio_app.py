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
    assert at.button(key="sample")  # empty canvas offers the sample


def test_sample_data_opens_a_finished_chart():
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    at.button(key="sample").click()
    at.run()
    assert not at.exception, at.exception
    assert not at.error, [e.value for e in at.error]
    spec = at.session_state.spec
    assert spec.chart.type == "line"
    assert spec.chart.y_cols == ["China", "India", "Russia", "United Kingdom"]
    assert len(at.get("image")) == 1


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

    at.segmented_control(key="inspector.section").set_value("Text")
    at.run()
    at.text_area(key="text.title").input("Maldives Gateway:\nMost Popular Airlines")
    at.segmented_control(key="chart.type").set_value("hbar")
    at.run()
    assert not at.exception
    assert not at.error, [e.value for e in at.error]
    assert at.session_state.spec.chart.type == "hbar"
    assert at.session_state.spec.chart.x_col == "Airline"
    assert at.session_state.spec.chart.y_cols == ["Total Passengers"]
    assert len(at.get("image")) == 1

    for ctype in ("line", "bar"):
        at.segmented_control(key="chart.type").set_value(ctype)
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


def test_bump_controls_update_spec():
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    at.session_state.raw_df = pd.DataFrame(
        {"Year": ["2021", "2022", "2023"], "EK": [3.0, 2.0, 1.0], "QR": [1.0, 3.0, 2.0]}
    )
    at.session_state.raw_key = "bump"
    at.run()
    at.segmented_control(key="chart.type").set_value("bump")
    at.run()
    at.slider(key="chart.other_alpha").set_value(0.25)
    at.run()
    assert not at.exception
    assert not at.error, [e.value for e in at.error]
    assert at.session_state.spec.chart.other_alpha == 0.25
    assert len(at.get("image")) == 1


def _sample_on_axes_tab():
    """A line chart over a real date column, with the Axes section open."""
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    at.session_state.raw_df = pd.DataFrame(
        {
            "Year": pd.to_datetime([f"{y}-01-01" for y in range(2019, 2025)]),
            "China": [281952, 14537, 5341, 80011, 194593, 262154],
            "India": [154327, 64906, 298835, 236932, 208493, 176336],
        }
    )
    at.session_state.raw_key = "dates"
    at.session_state.spec.chart.type = "line"
    at.session_state["chart.type"] = "line"
    at.session_state["inspector.section"] = "Axes"
    at.run()
    assert not at.exception, at.exception
    return at


def test_axes_date_preset_sets_format_and_warns_on_yearly_data():
    at = _sample_on_axes_tab()
    at.radio(key="axes.x_date_style").set_value("%b %Y")
    at.run()
    assert not at.exception, at.exception
    assert at.session_state.spec.style.axes.x_date_format == "%b %Y"
    assert any("yearly" in w.value for w in at.warning)


def test_axes_bad_custom_date_code_shows_message_not_error():
    at = _sample_on_axes_tab()
    at.radio(key="axes.x_date_style").set_value("custom")
    at.run()
    at.text_input(key="axes.x_date_format").set_value("%q")
    at.run()
    assert not at.exception, at.exception
    assert at.session_state.spec.style.axes.x_date_format is None
    assert any("%q" in w.value for w in at.warning)


def test_axes_bad_custom_number_format_shows_message_not_error():
    at = _sample_on_axes_tab()
    at.radio(key="axes.y_formatter").set_value("custom")
    at.run()
    at.text_input(key="axes.y_custom").set_value("{x")
    at.run()
    assert not at.exception, at.exception
    assert any("Can't read" in w.value for w in at.warning)


def test_axes_tab_hides_date_style_for_category_and_integer_year_x():
    at = _app_with_data()
    at.run()
    at.session_state["inspector.section"] = "Axes"
    at.run()
    assert not at.exception, at.exception
    assert "axes.x_date_style" not in at.session_state
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    at.button(key="sample").click()  # Year is whole numbers here
    at.run()
    at.session_state["inspector.section"] = "Axes"
    at.run()
    assert not at.exception, at.exception
    assert "axes.x_date_style" not in at.session_state


def _rail_states(at):
    html = " ".join(m.value for m in at.markdown if "ec-rail" in m.value)
    import re

    return re.findall(r'class="ec-step (\w+)"', html)


def test_rail_points_at_data_in_an_empty_session():
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    assert _rail_states(at) == ["next", "todo", "todo", "optional", "todo"]


def test_rail_after_sample_says_ready_to_export():
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    at.button(key="sample").click()
    at.run()
    assert not at.exception, at.exception
    assert _rail_states(at) == ["done", "done", "done", "optional", "next"]


def test_rail_asks_for_a_title_when_missing():
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    at.button(key="sample").click()
    at.run()
    at.session_state.spec.style.text.title = None
    at.session_state["text.title"] = ""
    at.session_state["inspector.section"] = "Text"
    at.run()
    assert _rail_states(at) == ["done", "done", "next", "optional", "todo"]


def test_mma_series_name_is_shown_after_fetch():
    at = _app_with_data()
    at.session_state.raw_key = "mma:101"
    at.session_state.source_label = "MMA series 101"
    at.session_state.series_info = {
        "name": "Quarterly GDP",
        "frequency": "Quarterly",
        "unit": "Rufiyaa",
    }
    at.run()
    assert not at.exception, at.exception
    assert any("Quarterly GDP" in m.value for m in at.markdown)
    assert any("MMA series 101 · Quarterly · Rufiyaa" in c.value for c in at.caption)


def test_theme_card_click_changes_theme():
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    at.button(key="sample").click()
    at.run()
    at.session_state["inspector.section"] = "Colors"
    at.run()
    assert not at.exception, at.exception
    at.button(key="colors.theme.consulting_dark").click()
    at.run()
    assert not at.exception, at.exception
    assert at.session_state.spec.style.colors.theme == "consulting_dark"
    assert any("ec-theme sel" in m.value for m in at.markdown)


def test_series_color_role_choice_is_kept_and_swatches_follow():
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    at.button(key="sample").click()
    at.run()
    at.session_state["inspector.section"] = "Colors"
    at.run()
    at.selectbox(key="colors.role.India").set_value("tertiary")
    at.run()
    assert not at.exception, at.exception
    assert at.session_state.spec.style.colors.color_map == {"India": "tertiary"}


def test_every_chart_type_renders_all_sections_without_error():
    for ctype in ("bar", "hbar", "line", "bump"):
        at = AppTest.from_file(STUDIO, default_timeout=60)
        at.run()
        at.button(key="sample").click()
        at.run()
        at.session_state["chart.type"] = ctype
        for section in ("Chart", "Text", "Axes", "Colors", "More"):
            at.session_state["inspector.section"] = section
            at.run()
            assert not at.exception, (ctype, section, at.exception)


def test_one_sided_axis_range_reaches_the_chart():
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    at.button(key="sample").click()
    at.run()
    at.segmented_control(key="inspector.section").set_value("Axes")
    at.run()
    at.number_input(key="axes.ylim.lo").set_value(0.0)  # Y max left on "auto"
    at.number_input(key="axes.xlim.hi").set_value(2030.0)  # X min left on "auto"
    at.run()
    assert not at.exception, at.exception
    assert not at.error, [e.value for e in at.error]
    axes = at.session_state.spec.style.axes
    assert axes.ylim == (0.0, None)
    assert axes.xlim == (None, 2030.0)
    assert len(at.get("image")) == 1


def _sample_app():
    at = AppTest.from_file(STUDIO, default_timeout=60)
    at.run()
    at.button(key="sample").click()
    at.run()
    return at


def _result(at):
    return at.session_state.pipeline_memo[1].df


def _last_step_key(at, suffix):
    return f"step.{at.session_state.step_ids[-1]}.{suffix}"


def test_scale_step_shows_values_in_thousands():
    at = _sample_app()
    before = _result(at)["China"].iloc[0]
    at.button(key="add_step.scale").click()
    at.run()
    assert not at.exception, at.exception
    assert not at.error, [e.value for e in at.error]
    assert _result(at)["China"].iloc[0] == pytest.approx(before / 1000)
    assert _result(at)["Year"].iloc[0] == 2019  # year labels are not scaled
    assert len(at.get("image")) == 1


def test_year_range_and_top_bottom_steps():
    at = _sample_app()
    at.button(key="add_step.date_filter").click()
    at.run()
    at.select_slider(key=_last_step_key(at, "years")).set_range(2021, 2023)
    at.run()
    assert not at.exception, at.exception
    assert _result(at)["Year"].tolist() == [2021, 2022, 2023]
    smallest = _result(at)["China"].min()
    at.button(key="add_step.top_n").click()
    at.run()
    at.segmented_control(key=_last_step_key(at, "which")).set_value("bottom")
    at.number_input(key=_last_step_key(at, "n")).set_value(1)
    at.selectbox(key=_last_step_key(at, "column")).set_value("China")
    at.run()
    assert not at.error, [e.value for e in at.error]
    res = _result(at)
    assert res["China"].tolist() == [smallest]


def test_date_steps_on_monthly_data():
    at = _app_with_data()
    at.session_state.raw_df = pd.DataFrame(
        {
            "Date": pd.date_range("2022-01-01", periods=24, freq="MS") + pd.Timedelta(days=14),
            "Sales": [float(i + 1) for i in range(24)],
        }
    )
    at.session_state.raw_key = "monthly"
    at.run()
    at.button(key="add_step.snap_dates").click()
    at.run()
    assert _result(at)["Date"].iloc[0] == pd.Timestamp("2022-01-31")
    at.button(key="add_step.resample").click()
    at.run()
    assert not at.exception, at.exception
    assert _result(at)["Sales"].tolist() == [78.0, 222.0]
    at.button(key="add_step.change").click()
    at.run()
    assert not at.error, [e.value for e in at.error]
    assert _result(at)["Sales"].iloc[0] == pytest.approx((222 / 78 - 1) * 100)
