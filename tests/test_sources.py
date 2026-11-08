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
