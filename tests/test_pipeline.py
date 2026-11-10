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
        .groupby("Airline")["Pax"]
        .sum()
        .sort_values(ascending=False)
        .head(1)
    )
    assert res.ok
    assert res.df["Airline"].tolist() == expected.index.tolist()
    assert res.df["Pax"].tolist() == expected.tolist()
    assert [s.status for s in res.steps] == ["ok"] * 4


@pytest.mark.parametrize(
    "op,value,expected",
    [
        ("=", "2022", 2),
        ("≠", "2022", 5),
        (">", "2021", 5),
        ("≥", "2022", 5),
        ("<", "2022", 2),
        ("≤", "2022", 4),
        ("in", "2021, 2023", 5),
    ],
)
def test_filter_operators_coerce_numeric(flights, op, value, expected):
    step = {"op": "filter", "params": {"column": "Year", "operator": op, "value": value}}
    res = apply_steps(flights, [step])
    assert res.ok, res.steps[0].error
    assert len(res.df) == expected


def test_group_count_and_mean(flights):
    res = apply_steps(flights, [StepSpec("group", {"by": ["Year"], "agg": "count"})])
    assert res.df.set_index("Year")["count"].to_dict() == {2021: 2, 2022: 2, 2023: 3}
    res = apply_steps(flights, [StepSpec("group", {"by": ["Year"], "agg": "mean"})])
    assert res.df.set_index("Year")["Pax"].loc[2021] == 7.5


def test_pivot_long_to_wide(flights):
    step = StepSpec("pivot", {"index": "Year", "columns": "Airline", "values": "Pax"})
    res = apply_steps(flights, [step])
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
    step = StepSpec("filter", {"column": "Pax", "operator": ">", "value": "abc"})
    res = apply_steps(flights, [step])
    assert res.failed_index == 0
    assert "number" in res.steps[0].error


def test_input_not_mutated(flights):
    before = flights.copy()
    apply_steps(flights, [StepSpec("sort", {"column": "Pax"}), StepSpec("top_n", {"n": 2})])
    pd.testing.assert_frame_equal(flights, before)


# ── dates ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def monthly():
    dates = pd.date_range("2022-01-01", periods=24, freq="MS") + pd.Timedelta(days=14)
    return pd.DataFrame({"Date": dates, "Sales": [float(i + 1) for i in range(24)]})


def _run(df, op, **params):
    res = apply_steps(df, [StepSpec(op, params)])
    assert res.ok, res.steps[0].error
    return res.df


@pytest.mark.parametrize(
    "to,expected",
    [
        ("month_end", "2022-01-31"),
        ("month_start", "2022-01-01"),
        ("quarter_end", "2022-03-31"),
        ("quarter_start", "2022-01-01"),
        ("year_end", "2022-12-31"),
        ("year_start", "2022-01-01"),
    ],
)
def test_snap_dates(monthly, to, expected):
    out = _run(monthly, "snap_dates", column="Date", to=to)
    assert out["Date"].iloc[0] == pd.Timestamp(expected)
    assert len(out) == len(monthly)


def test_snap_dates_keeps_dates_already_on_month_end():
    df = pd.DataFrame({"Date": pd.to_datetime(["2024-01-31", "2024-02-29"]), "v": [1, 2]})
    out = _run(df, "snap_dates", column="Date", to="month_end")
    assert out["Date"].tolist() == df["Date"].tolist()


def test_snap_dates_needs_a_date_column(flights):
    res = apply_steps(flights, [StepSpec("snap_dates", {"column": "Year", "to": "month_end"})])
    assert res.failed_index == 0
    assert "date" in res.steps[0].error


def test_date_filter_years_and_months(monthly):
    out = _run(monthly, "date_filter", column="Date", years=[2023, 2023], months=[6, 12])
    assert out["Date"].dt.strftime("%Y-%m").tolist() == ["2023-06", "2023-12"]


def test_date_filter_blank_months_keeps_whole_years(monthly):
    out = _run(monthly, "date_filter", column="Date", years=[2023, 2023])
    assert len(out) == 12


def test_date_filter_on_year_numbers(flights):
    out = _run(flights, "date_filter", column="Year", years=[2022, 2023])
    assert sorted(out["Year"].unique()) == [2022, 2023]


def test_date_filter_months_need_real_dates(flights):
    res = apply_steps(flights, [StepSpec("date_filter", {"column": "Year", "months": [1]})])
    assert res.failed_index == 0


@pytest.mark.parametrize(
    "period,agg,first", [("year", "sum", 78.0), ("year", "last", 12.0), ("quarter", "mean", 2.0)]
)
def test_resample(monthly, period, agg, first):
    out = _run(monthly, "resample", column="Date", period=period, agg=agg)
    assert out["Sales"].iloc[0] == first
    assert len(out) == {"year": 2, "quarter": 8}[period]


def test_resample_labels_periods_by_their_end(monthly):
    out = _run(monthly, "resample", column="Date", period="year", agg="sum")
    assert out["Date"].tolist() == [pd.Timestamp("2022-12-31"), pd.Timestamp("2023-12-31")]


def test_resample_keeps_text_columns_as_groups():
    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-31", "2024-02-29"] * 2),
            "Market": ["A", "A", "B", "B"],
            "v": [1.0, 2.0, 10.0, 20.0],
        }
    )
    out = _run(df, "resample", column="Date", period="year", agg="sum")
    assert out.set_index("Market")["v"].to_dict() == {"A": 3.0, "B": 30.0}


# ── numbers ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "unit,factor,expected",
    [("thousands", None, 1.5), ("hundreds", None, 15.0), ("custom", 3, 500.0)],
)
def test_scale_divides_values(unit, factor, expected):
    df = pd.DataFrame({"Label": ["a"], "v": [1500.0], "w": [3000.0]})
    out = _run(df, "scale", columns=["v"], unit=unit, factor=factor)
    assert out["v"].iloc[0] == expected
    assert out["w"].iloc[0] == 3000.0  # only the chosen column


def test_scale_blank_columns_means_every_number_column(flights):
    out = _run(flights, "scale", unit="thousands")
    assert out["Pax"].iloc[0] == pytest.approx(0.01)
    assert out["Year"].iloc[0] == 2021  # year-like whole numbers are left alone


def test_scale_rejects_zero():
    df = pd.DataFrame({"v": [1.0]})
    res = apply_steps(df, [StepSpec("scale", {"unit": "custom", "factor": 0})])
    assert res.failed_index == 0


@pytest.mark.parametrize(
    "kind,expected",
    [
        ("pct_prev", [100.0, 50.0]),
        ("diff_prev", [1.0, 1.0]),
        ("index", [100.0, 200.0, 300.0]),
    ],
)
def test_change(kind, expected):
    df = pd.DataFrame({"Year": [2021, 2022, 2023], "v": [1.0, 2.0, 3.0]})
    out = _run(df, "change", columns=["v"], kind=kind)
    assert out["v"].tolist() == pytest.approx(expected)


def test_change_year_on_year_for_monthly_data(monthly):
    out = _run(monthly, "change", columns=["Sales"], kind="yoy", date_column="Date")
    assert len(out) == 12  # the first year has nothing to compare with
    assert out["Sales"].iloc[0] == pytest.approx((13 / 1 - 1) * 100)


def test_rolling_average():
    df = pd.DataFrame({"x": [1, 2, 3, 4], "v": [1.0, 2.0, 3.0, 4.0]})
    out = _run(df, "rolling", columns=["v"], window=2)
    assert out["v"].tolist() == [1.5, 2.5, 3.5]
    assert out["x"].tolist() == [2, 3, 4]


# ── rows / shape ──────────────────────────────────────────────────────────────


def test_top_n_by_column(flights):
    out = _run(flights, "top_n", n=2, column="Pax", which="top")
    assert out["Pax"].tolist() == [15.0, 12.0]


def test_bottom_n_by_column(flights):
    out = _run(flights, "top_n", n=2, column="Pax", which="bottom")
    assert out["Pax"].tolist() == [3.0, 5.0]


def test_bottom_n_without_column_keeps_last_rows(flights):
    out = _run(flights, "top_n", n=2, which="bottom")
    assert out["Airline"].tolist() == ["QR", "UL"]


def test_rename(flights):
    out = _run(flights, "rename", column="Pax", to="Passengers (m)")
    assert "Passengers (m)" in out.columns and "Pax" not in out.columns


def test_rename_refuses_existing_name(flights):
    res = apply_steps(flights, [StepSpec("rename", {"column": "Pax", "to": "Year"})])
    assert res.failed_index == 0
