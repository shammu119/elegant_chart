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
