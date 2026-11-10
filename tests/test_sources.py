import io

import pandas as pd
import pytest

from elegant_chart import sources


def test_read_csv():
    df = sources.read_uploaded(b"a,b\n1,2\n3,4\n", "data.csv")
    assert df.to_dict("list") == {"a": [1, 3], "b": [2, 4]}


def test_excel_sheets_and_read():
    pytest.importorskip("openpyxl")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame({"x": [1]}).to_excel(w, sheet_name="First", index=False)
        pd.DataFrame({"y": [2, 3]}).to_excel(w, sheet_name="Second", index=False)
    data = buf.getvalue()
    assert sources.list_sheets(data) == ["First", "Second"]
    assert list(sources.read_uploaded(data, "book.xlsx", "Second").columns) == ["y"]
    assert list(sources.read_uploaded(data, "book.xlsx").columns) == ["x"]


def test_unsupported_type():
    with pytest.raises(ValueError):
        sources.read_uploaded(b"", "image.png")


def test_mma_uses_get_series_df(monkeypatch):
    import elegant_chart.get_api_data as api

    monkeypatch.setattr(api, "get_series_df", lambda sid: pd.DataFrame({"id": [sid]}))
    assert sources.load_mma_series("101")["id"].tolist() == [101]


def test_csv_iso_dates_become_datetimes():
    df = sources.read_uploaded(b"Month,Code,Value\n2024-01-01,A1,1\n2024-02-01,B2,2\n", "data.csv")
    assert pd.api.types.is_datetime64_any_dtype(df["Month"])
    assert df["Code"].tolist() == ["A1", "B2"]  # non-date text untouched


def test_mixed_text_column_not_converted():
    df = sources.read_uploaded(b"When\n2024-01-01\nsoon\n", "data.csv")
    assert df["When"].tolist() == ["2024-01-01", "soon"]


def test_series_info_reads_name_frequency_unit(monkeypatch):
    import elegant_chart.get_api_data as api

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "data": [
                    {
                        "id": 101,
                        "name": "Quarterly GDP",
                        "frequency": "Quarterly",
                        "unit": "Rufiyaa",
                        "path": ["ignored"],
                        "data": [],
                    }
                ]
            }

    monkeypatch.setenv("MMA_API_TOKEN", "t")
    monkeypatch.setattr("requests.get", lambda *a, **k: Resp())
    info = api.get_series_info(101)
    assert info == {"name": "Quarterly GDP", "frequency": "Quarterly", "unit": "Rufiyaa"}


def test_series_info_failure_returns_empty(monkeypatch):
    import elegant_chart.get_api_data as api

    monkeypatch.delenv("MMA_API_TOKEN", raising=False)
    monkeypatch.chdir("/")  # no TOKEN.txt here
    assert api.get_series_info(101) == {}


def test_load_mma_info_delegates(monkeypatch):
    import elegant_chart.get_api_data as api

    monkeypatch.setattr(api, "get_series_info", lambda sid: {"name": f"s{sid}"})
    assert sources.load_mma_info("7") == {"name": "s7"}


@pytest.mark.parametrize(
    "values, expected_first",
    [
        (["2024-01-31", "2024-02-29"], "2024-01-31"),  # ISO (MMA series)
        (["2024-01", "2024-02"], "2024-01-01"),  # ISO year-month
        (["Jan 2024", "Feb 2024"], "2024-01-01"),
        (["January 2024", "February 2024"], "2024-01-01"),
        (["Jan-24", "Feb-24"], "2024-01-01"),
        (["15 Jan 2024", "16 Feb 2024"], "2024-01-15"),
        (["Jan 15, 2024", "Feb 16, 2024"], "2024-01-15"),
        (["31/01/2024", "29/02/2024"], "2024-01-31"),  # day-first
        (["01/31/2024", "02/29/2024"], "2024-01-31"),  # only month-first fits
        (["01/02/2024", "03/02/2024"], "2024-02-01"),  # ambiguous -> day-first
        (["2024/01/31", "2024/02/29"], "2024-01-31"),
    ],
)
def test_text_dates_in_common_formats_are_detected(values, expected_first):
    df = sources.parse_date_columns(pd.DataFrame({"d": values, "v": [1, 2]}))
    assert pd.api.types.is_datetime64_any_dtype(df["d"])
    assert df["d"].iloc[0] == pd.Timestamp(expected_first)


@pytest.mark.parametrize(
    "values",
    [
        ["2021", "2022"],  # year labels stay categories/numbers
        ["Jan", "Feb"],  # month names alone are categories
        ["2021-22", "2022-23"],  # fiscal years
        ["A1", "B2"],
        ["Jan 2024", "soon"],  # one stray value -> leave the column alone
    ],
)
def test_non_date_text_is_left_alone(values):
    df = sources.parse_date_columns(pd.DataFrame({"d": values}))
    assert df["d"].tolist() == values


def test_blank_cells_do_not_block_detection():
    df = sources.parse_date_columns(pd.DataFrame({"d": ["Jan 2024", None, "Mar 2024"]}))
    assert pd.api.types.is_datetime64_any_dtype(df["d"])
    assert df["d"].isna().tolist() == [False, True, False]


def test_numeric_columns_are_never_converted():
    df = sources.parse_date_columns(pd.DataFrame({"Year": [2021, 2022], "v": [1.5, 2.5]}))
    assert df["Year"].tolist() == [2021, 2022]


def test_excel_text_dates_become_datetimes():
    pytest.importorskip("openpyxl")
    buf = io.BytesIO()
    pd.DataFrame({"date": ["2024-01-31", "2024-02-29"], "amount": [1.0, 2.0]}).to_excel(
        buf, index=False
    )
    df = sources.read_uploaded(buf.getvalue(), "book.xlsx")
    assert pd.api.types.is_datetime64_any_dtype(df["date"])


def test_mma_series_dates_become_datetimes(monkeypatch):
    import elegant_chart.get_api_data as api

    monkeypatch.setattr(
        api,
        "get_series_df",
        lambda sid: pd.DataFrame({"date": ["2010-01-31", "2010-02-28"], "amount": [1.0, 2.0]}),
    )
    assert pd.api.types.is_datetime64_any_dtype(sources.load_mma_series(217)["date"])
