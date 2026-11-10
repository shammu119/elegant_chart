"""Pure helpers behind Chart Studio's previews, checklist and theme cards."""

import pandas as pd

from elegant_chart.app import ux

YEARS = [pd.Timestamp(y, 1, 1) for y in range(2019, 2025)]  # yearly dates


def test_sample_dates_accepts_real_dates():
    dates = ux.sample_dates(YEARS)
    assert [d.year for d in dates] == [2019, 2020, 2021, 2022, 2023, 2024]


def test_sample_dates_rejects_plain_year_numbers():
    # The chart does not apply a date format to integer years, so no preview.
    assert ux.sample_dates([2019, 2020, 2021]) is None


def test_sample_dates_keeps_first_and_last_and_caps_at_six():
    dates = ux.sample_dates(pd.date_range("2003-03-31", periods=94, freq="QE"))
    assert len(dates) == 6
    assert dates[0] == pd.Timestamp("2003-03-31")
    assert dates[-1] == pd.Timestamp("2026-06-30")


def test_sample_dates_none_for_categories():
    assert ux.sample_dates(["Emirates", "Qatar Airways"]) is None
    assert ux.sample_dates([]) is None


def test_date_preview_year():
    p = ux.date_label_preview("%Y", ux.sample_dates(YEARS))
    assert p.labels == ["2019", "2020", "2021", "2022", "2023", "2024"]
    assert p.problem is None


def test_date_preview_short_month_year():
    p = ux.date_label_preview(
        "%b %y", ux.sample_dates(pd.date_range("2024-01-31", periods=3, freq="ME"))
    )
    assert p.labels == ["Jan 24", "Feb 24", "Mar 24"]
    assert p.problem is None


def test_date_preview_flags_month_on_yearly_data():
    p = ux.date_label_preview("%b %y", ux.sample_dates(YEARS))
    assert p.labels[0] == "Jan 19"
    assert "yearly" in p.problem


def test_date_preview_flags_unknown_code_and_missing_year():
    dates = ux.sample_dates(YEARS)
    assert "%q" in ux.date_label_preview("%q", dates).problem
    assert "year" in ux.date_label_preview("%b", dates).problem
    assert ux.date_label_preview("", dates).problem is not None
    assert ux.date_label_preview("%", dates).problem is not None


def test_format_value_matches_library_formatters():
    assert ux.format_value("compact", 298835) == "298.8K"
    assert ux.format_value("compact", 14537) == "14.5K"
    assert ux.format_value("compact", 1_200_000) == "1.2M"
    assert ux.format_value("plain", 298835) == "298835"
    assert ux.format_value("percent", 0.1) == "10%"
    assert ux.format_value("norm_max", 100, decimals=0, max_value=100) == "1"
    assert ux.format_value("norm_max", 50, decimals=1, max_value=100) == "0.5"


def test_format_value_custom_and_bad_custom():
    assert ux.format_value("custom", 298835, custom="{x:,.1f}") == "298,835.0"
    assert ux.format_value("custom", 298835, custom="{x") is None
    assert ux.format_value("custom", 298835, custom="{y}") is None
    assert ux.value_style_problem("{x:,.1f}") is None
    assert ux.value_style_problem("{x") is not None


def test_checklist_empty_session_points_at_data():
    items = ux.checklist(has_data=False, chart_ready=False, has_title=False)
    assert [i.key for i in items] == ["data", "chart", "titles", "look", "export"]
    assert [i.key for i in items if i.state == "next"] == ["data"]
    assert items[3].state == "optional"


def test_checklist_moves_next_step_and_unlocks_export():
    items = ux.checklist(has_data=True, chart_ready=True, has_title=False)
    assert [i.state for i in items] == ["done", "done", "next", "optional", "todo"]
    items = ux.checklist(has_data=True, chart_ready=True, has_title=True)
    assert [i.state for i in items] == ["done", "done", "done", "optional", "next"]
    assert items[-1].hint.lower().startswith("ready")


def test_series_chip():
    info = {"name": "Quarterly GDP", "frequency": "Quarterly", "unit": "Rufiyaa"}
    assert ux.series_chip(info, 94) == "Quarterly GDP · Quarterly · Rufiyaa · 94 rows"
    assert ux.series_chip({}, 94) is None
    assert ux.series_chip(None, 94) is None


def test_theme_helpers():
    assert ux.theme_palette("newsroom_dark")[0] == "#4C72B0"
    assert ux.theme_bg("newsroom_dark") == "#0b1014"
    svg = ux.theme_thumbnail_svg("newsroom_dark", [[1, 2, 3], [3, 2, 1]])
    assert svg.startswith("<svg") and svg.count("<polyline") == 2 and "#0b1014" in svg
    assert ux.theme_thumbnail_svg("newsroom_dark", []).count("<polyline") == 0


# ── reshape step previews ────────────────────────────────────────────────────


def test_before_after_shows_first_changed_date():
    before = pd.Series(pd.to_datetime([None, "2024-01-15"]))
    after = pd.Series(pd.to_datetime([None, "2024-01-31"]))
    assert ux.before_after(before, after) == "15 Jan 2024 → 31 Jan 2024"


def test_before_after_shows_numbers_compactly():
    assert ux.before_after(pd.Series([1234567.0]), pd.Series([1234.567])) == "1,234,567 → 1,234.57"


def test_before_after_is_none_without_values():
    assert ux.before_after(pd.Series([None]), pd.Series([None])) is None


def test_year_options_from_dates_and_year_numbers():
    dates = pd.Series(pd.to_datetime(["2022-03-31", "2021-12-31", "2022-06-30"]))
    assert ux.year_options(dates) == [2021, 2022]
    assert ux.year_options(pd.Series([2020, 2019, 2020])) == [2019, 2020]
    assert ux.year_options(pd.Series(["a", "b"])) == []


MONTHS_2026 = [pd.Timestamp(2026, m, 1) for m in (1, 2, 3)]


def test_month_initial_presets_preview_like_the_chart():
    assert ux.date_label_preview("%J", MONTHS_2026).labels == ["J", "F", "M"]
    preview = ux.date_label_preview("%b|%J", MONTHS_2026)
    assert preview.labels == ["Jan", "F", "M"] and preview.problem is None
    assert ("%J", "Month initial") in ux.DATE_PRESETS


def test_first_label_split_must_have_two_parts():
    assert ux.date_label_preview("%b|%J|%m", MONTHS_2026).problem
    assert ux.date_label_preview("%b|", MONTHS_2026).problem
