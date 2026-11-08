# Chart Studio hand-held UX — Implementation Plan

> **For agentic workers:** use superpowers:executing-plans. Steps use checkbox syntax.

**Goal:** Make Chart Studio self-explanatory: previews instead of codes, plain labels, a progress rail, real colors.

**Architecture:** Pure, Streamlit-free helpers in `src/elegant_chart/app/ux.py` (tested directly), consumed by `studio.py`. `ChartSpec` is unchanged. One new library function returns MMA series metadata.

**Tech Stack:** Streamlit ≥1.50, pandas, pytest (`AppTest` for the app).

**Spec:** `docs/superpowers/specs/2026-11-08-studio-ux-handholding-design.md`. Mockup picks: Axes = A1 + B2 + C wording; Checklist = A rail + series chip; Colors = B1 theme cards + A2 swatch rows + chart-type icons.

## Global Constraints
- Output stays 1080×1350 @ 500 DPI; no change to chart rendering or `ChartSpec` fields.
- `ruff format --check src tests` and `ruff check src tests` clean; `pytest` green.
- Previews must match the library's real formatters (`axis_mixin._build_formatter`).

## Review Focus
- Invalid date codes (`%q`, empty, trailing `%`) show a message, never raise.
- Invalid custom number format (`{x`, `{y}`, `{x:d}` on a float) shows a message, never raises.
- Non-date x columns (categories) hide the date-format control instead of previewing garbage.
- No data loaded: checklist, previews and theme cards all render without a DataFrame.
- MMA metadata fetch failure still loads the data (name chip omitted).

---

### Task 1: Pure helpers (`ux.py`)
**Files:** Create `src/elegant_chart/app/ux.py`; Test `tests/test_ux.py`.
**Produces:**
- `sample_dates(values: Sequence) -> list[pd.Timestamp] | None` — up to 6 evenly spread dates (first, last always included); ints 1900–2100 are years; unparseable → `None`.
- `date_label_preview(code: str, dates) -> DatePreview(labels: list[str], problem: str | None)`; problems: unknown code, missing year, month on yearly data.
- `DATE_PRESETS: tuple[tuple[str, str], ...]` = (`%Y`,"Year"), (`%y`,"Short year"), (`%b %Y`,"Month and year"), (`%B %Y`,"Full month and year").
- `format_value(style: str, x: float, decimals: int = 0, custom: str = "") -> str | None` mirroring the library; `None` on a bad custom string; `value_style_problem(custom) -> str | None`.
- `checklist(*, has_data: bool, chart_ready: bool, has_title: bool) -> list[ChecklistItem(key, label, state, hint)]`, state ∈ `done|next|optional|todo`, exactly one `next`.
- `series_chip(info: dict | None, rows: int) -> str | None`.
- `theme_palette(theme: str) -> tuple[str, ...]`, `theme_bg(theme) -> str`, `theme_thumbnail_svg(theme, series: Sequence[Sequence[float]]) -> str`.
- [ ] Tests first (assert exact labels, e.g. `%Y` on 2019..2024 → `["2019",…,"2024"]`, `%b %y` flags "month on yearly data", `{x:,.1f}` on 298835 → `"298,835.0"`, `{x` → `None`).
- [ ] Implement, run `pytest tests/test_ux.py`, commit.

### Task 2: MMA series metadata
**Files:** Modify `src/elegant_chart/get_api_data.py`, `src/elegant_chart/sources.py`; Test `tests/test_sources.py`.
**Produces:** `get_series_info(series_id: int, timeout: int = 30) -> dict` (keys `name`, `frequency`, `unit`, `last_updated_at`; `{}` on any failure) and `sources.load_mma_info(series_id) -> dict`.
- [ ] Test with a mocked `requests.get`; failure returns `{}`.
- [ ] Implement, commit.

### Task 3: Axes tab
**Files:** Modify `studio.py` (`axes_tab`); Test `tests/test_studio_app.py`.
- [ ] Date style radio of presets showing the result (`2019 … 2024  ·  %Y`) plus "Custom…" text box with live result; hidden for non-date x. Live axis strip under it (HTML, tick marks).
- [ ] Value format radio showing the result for the data's largest value, Custom with live result.
- [ ] Plain wording for tick controls (spec fields unchanged).
- [ ] AppTest: choosing a preset sets `spec.style.axes.x_date_format`; bad custom code shows a message, no exception.

### Task 4: Progress rail + series chip
**Files:** Modify `studio.py` (`data_panel`, `_CSS`); Test `tests/test_studio_app.py`.
- [ ] Rail at top of the sidebar from `ux.checklist`; chip after Fetch from `ux.series_chip`.
- [ ] AppTest: empty session → "Data" is next; sample loaded → "Export" is ready, title present.

### Task 5: Colors, chart type, plain labels
**Files:** Modify `studio.py` (`colors_tab`, `chart_type_control`, `_step_controls`, `layout_tab`).
- [ ] Theme cards drawn as mini charts of the user's data (`ux.theme_thumbnail_svg`), click to apply.
- [ ] Series rows: dot + name + "auto → primary" + five-swatch strip; select keeps role/custom.
- [ ] Material icons on chart-type options; plain step labels (Condition, How many rows to keep, Rows (x-axis), Series (one per…)).
- [ ] AppTest: switching theme updates `spec.style.colors.theme`; no exceptions on all four chart types.

### Task 6: Verify
- [ ] `ruff format --check`, `ruff check`, `pytest -q`; run the app and screenshot each section against the mockup; commit; push to `main`.
