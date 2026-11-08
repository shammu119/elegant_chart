import pandas as pd
import pytest

from elegant_chart.pipeline import apply_steps
from elegant_chart.spec import StepSpec


@pytest.fixture
def flights():
    return pd.DataFrame(
        {
            "Year": [2021, 2021, 2022, 2022, 2023, 2023, 2023],
            "Airline": ["EK", "QR", "EK", "QR", "EK", "QR", "UL"],
            "Type": ["International"] * 6 + ["Domestic"],
            "Pax": [10.0, 5.0, 12.0, 8.0, 15.0, 9.0, 3.0],
        }
    )


def test_airline_example_matches_hand_written_pandas(flights):
    steps = [
        StepSpec("filter", {"column": "Type", "operator": "=", "value": "International"}),
        StepSpec("group", {"by": ["Airline"], "agg": "sum", "columns": ["Pax"]}),
        StepSpec("sort", {"column": "Pax", "ascending": False}),
        StepSpec("top_n", {"n": 1}),
    ]
    res = apply_steps(flights, steps)
    expected = (
        flights[flights["Type"] == "International"]
        .groupby("Airline")["Pax"].sum().sort_values(ascending=False).head(1)
    )
    assert res.ok
    assert res.df["Airline"].tolist() == expected.index.tolist()
    assert res.df["Pax"].tolist() == expected.tolist()
    assert [s.status for s in res.steps] == ["ok"] * 4


@pytest.mark.parametrize(
    "op,value,expected",
    [("=", "2022", 2), ("≠", "2022", 5), (">", "2021", 5), ("≥", "2022", 5),
     ("<", "2022", 2), ("≤", "2022", 4), ("in", "2021, 2023", 5)],
)
def test_filter_operators_coerce_numeric(flights, op, value, expected):
    res = apply_steps(flights, [{"op": "filter", "params": {"column": "Year", "operator": op, "value": value}}])
    assert res.ok, res.steps[0].error
    assert len(res.df) == expected


def test_group_count_and_mean(flights):
    res = apply_steps(flights, [StepSpec("group", {"by": ["Year"], "agg": "count"})])
    assert res.df.set_index("Year")["count"].to_dict() == {2021: 2, 2022: 2, 2023: 3}
    res = apply_steps(flights, [StepSpec("group", {"by": ["Year"], "agg": "mean"})])
    assert res.df.set_index("Year")["Pax"].loc[2021] == 7.5


def test_pivot_long_to_wide(flights):
    res = apply_steps(flights, [StepSpec("pivot", {"index": "Year", "columns": "Airline", "values": "Pax"})])
    assert res.ok, res.steps[0].error
    assert list(res.df.columns) == ["Year", "EK", "QR", "UL"]
    assert res.df.set_index("Year").loc[2023, "UL"] == 3.0


def test_failure_stops_pipeline_and_keeps_last_good(flights):
    steps = [
        StepSpec("filter", {"column": "Type", "operator": "=", "value": "International"}),
        StepSpec("sort", {"column": "Missing", "ascending": True}),
        StepSpec("top_n", {"n": 2}),
    ]
    res = apply_steps(flights, steps)
    assert res.failed_index == 1
    assert "Missing" in res.steps[1].error
    assert [s.status for s in res.steps] == ["ok", "error", "skipped"]
    assert len(res.df) == 6  # output of step 0


def test_bad_number_reports_error(flights):
    res = apply_steps(flights, [StepSpec("filter", {"column": "Pax", "operator": ">", "value": "abc"})])
    assert res.failed_index == 0
    assert "number" in res.steps[0].error


def test_input_not_mutated(flights):
    before = flights.copy()
    apply_steps(flights, [StepSpec("sort", {"column": "Pax"}), StepSpec("top_n", {"n": 2})])
    pd.testing.assert_frame_equal(flights, before)
