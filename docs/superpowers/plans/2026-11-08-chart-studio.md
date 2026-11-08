# Chart Studio Implementation Plan

> Spec: `docs/superpowers/specs/2026-11-08-chart-studio-design.md`
> Design rules: `CLAUDE.md` (the renderer owns them; the app only passes parameters)

**Goal:** A local Streamlit GUI that goes from raw data (MMA API or Excel/CSV)
through an ordered reshape pipeline to a finished Elegant Chart PNG, with a
live preview produced by the real matplotlib renderer, and downloads of the
1080 × 1350 px / 500 DPI PNG plus `chart_data.xlsx`.

**Architecture:** Three new library layers, then a thin GUI on top.

```
data source ──► apply_steps(df, steps) ──► render(spec, df) ──► Figure
 (io.py)          (pipeline.py)             (render.py)          │
                                                                 ├─► preview PNG (low DPI, same figsize)
ChartSpec (spec.py) ── drives all three ─────────────────────────└─► download PNG (500 DPI) + xlsx
     ▲
     └── Streamlit widgets (app/studio.py) map one-to-one onto spec fields
```

- `ChartSpec` is a tree of plain dataclasses (`to_dict` / `from_dict`), so the
  GUI never has to know the library's constructor-vs-call-argument split.
- `render()` routes each spec field to `ElegantChart(...)` or to
  `bar()/line()/bump()` exactly as the library expects today. **No library
  parameter is refactored**, so existing scripts and tests keep working.
- Preview vs export: the figure is built once at the canonical
  `figsize=(2.16, 2.70)`; only `savefig(dpi=…)` differs. Layout is computed in
  figure fractions, so preview and export are the same image at different
  resolutions.

**Tech stack:** Python ≥ 3.12, pandas, matplotlib (existing), Streamlit
(new optional group `elegant_chart[app]`), pytest.

---

## File map

| File | Responsibility |
|---|---|
| `src/elegant_chart/spec.py` | `ChartSpec` and nested dataclasses; `to_dict`/`from_dict`; constants (`CHART_TYPES`, `STEP_OPS`, …) |
| `src/elegant_chart/pipeline.py` | `apply_steps(df, steps) -> PipelineResult`; one pure pandas op per step; stops at first failure |
| `src/elegant_chart/io.py` | `load_source(...)`: MMA via `get_series_df`, CSV/XLSX bytes → DataFrame, `list_sheets` |
| `src/elegant_chart/render.py` | `build_chart_kwargs`, `build_call_kwargs`, `render(spec, df) -> RenderResult`, `figure_png_bytes`, `chart_data_xlsx_bytes` |
| `src/elegant_chart/app/__init__.py` | `main()` console entry: launches `streamlit run studio.py` |
| `src/elegant_chart/app/__main__.py` | `python -m elegant_chart.app` |
| `src/elegant_chart/app/studio.py` | Streamlit script: three panels, widgets ↔ spec, preview, downloads |
| `tests/test_spec.py`, `tests/test_pipeline.py`, `tests/test_render.py`, `tests/test_io.py` | Unit tests for the library layers |
| `tests/test_studio_app.py` | Streamlit `AppTest` smoke test (skipped if Streamlit not installed) |
| `pyproject.toml` | `app` extra + `elegant-chart-studio` script |
| `README.md` / `USAGE.md` | How to install and launch Chart Studio; `render(ChartSpec(...))` from Python |

---

## Task 1 — ChartSpec

**Files:** create `src/elegant_chart/spec.py`, `tests/test_spec.py`

Shape (field names final):

```
ChartSpec
├── source: SourceSpec(kind="mma"|"file"|"none", series_id, name, sheet)
├── steps:  list[StepSpec(op, params: dict)]
├── chart:  ChartTypeSpec(type="bar"|"hbar"|"line"|"bump", x_col, y_cols,
│            stacked, bar_width, markers, linewidth, rotation, compact_years,
│            highlight, ascending, show_value_labels, logos: dict[label, path])
└── style:  StyleSpec
     ├── text:   title, subtitle, caption, xlabel, ylabel, annotations: list[dict]
     ├── layout: x_upper_pad, align_x_edges, tick_label_pad, max_label_width,
     │           label_width_strategy, logo_mode("default"|"none"|"custom"),
     │           logo_path, show_footer, y_axis_side, y_tick_labels_inside,
     │           show_y_axis, show_y_spine
     ├── axes:   x_tick_step, max_x_ticks, auto_x_thinning, y_tick_step,
     │           max_y_ticks, x_date_format, x_minor_ticks, x_year_tick_interval,
     │           xlim, ylim, y_formatter, y_formatter_decimals
     ├── colors: theme, color_map: dict[label, role|hex], alpha_map: dict[label, float]
     └── legend: legend_ncol
```

Steps:
1. Write failing tests: defaults construct; `from_dict(to_dict(spec)) == spec`
   (round trip incl. nested lists/tuples); unknown keys in `from_dict` are
   ignored; changing `chart.type` leaves `style` untouched.
2. Implement dataclasses with `field(default_factory=…)`; `to_dict` via
   `dataclasses.asdict`; `from_dict` builds each sub-dataclass, converting
   `xlim`/`ylim` lists back to tuples.
3. `pytest tests/test_spec.py` → pass. Commit.

## Task 2 — Reshape pipeline

**Files:** create `src/elegant_chart/pipeline.py`, `tests/test_pipeline.py`

- Ops: `filter` (`column, operator in = ≠ > ≥ < ≤ in, value`), `group`
  (`by: list, agg: sum|mean|count|min|max, columns: list|None`), `sort`
  (`column, ascending`), `top_n` (`n`), `pivot` (`index, columns, values`,
  aggregated with `sum` so duplicates don't raise).
- Value coercion for `filter`: when the column is numeric, cast the value
  with `float`; for datetimes, `pd.to_datetime`; `in` splits on commas.
- `PipelineResult(df, step_results: list[StepResult(ok, error, rows)], failed_index)`.
  On the first exception: record the message, stop, return the last good df.
  Steps after the failure are reported as `skipped`.

Steps:
1. Failing tests: each op on a small frame; the airline example
   (filter Type=International → group Airline sum → sort desc → top 10)
   matches the hand-written pandas in `examples/series_101_top10_airlines.py`;
   a filter on a missing column → `failed_index == i`, error mentions the
   column, df equals the previous step's output, later steps skipped;
   input df is not mutated.
2. Implement. 3. Tests pass. Commit.

## Task 3 — Data sources

**Files:** create `src/elegant_chart/io.py`, `tests/test_io.py`

- `list_sheets(data: bytes) -> list[str]` (xlsx only).
- `read_uploaded(data: bytes, name: str, sheet: str|None) -> DataFrame`
  (CSV via `pd.read_csv`, XLSX via `pd.read_excel(sheet_name=…)`).
- `load_mma_series(series_id) -> DataFrame` — thin wrapper over
  `get_series_df`; the token never passes through the app.

Steps: tests with in-memory CSV and a two-sheet XLSX (openpyxl); implement; commit.

## Task 4 — render(spec, df)

**Files:** create `src/elegant_chart/render.py`, `tests/test_render.py`;
export `ChartSpec`, `render`, `apply_steps` from `__init__.py`.

Routing (mirrors today's API, no refactor):

| Spec field | `ElegantChart(...)` | `bar()` | `line()` | `bump()` |
|---|---|---|---|---|
| text.*, colors.theme/color_map, legend_ncol, logo, footer, y-axis side/inside/show/spine, annotations | ✓ | | | |
| axes.x/y tick steps, max ticks, thinning, xlim, ylim, x_minor_ticks, x_date_format, x_upper_pad, align_x_edges, y_formatter | ✓ (constructor holds shared defaults) | per-call where the method takes it | per-call | — |
| max_label_width, label_width_strategy, tick_label_pad, rotation, compact_years, show_value_labels, alpha_map | | ✓ | ✓ | — |
| stacked, bar_width, horizontal (type=hbar), logos→`y_tick_logos` (hbar) | | ✓ | | |
| markers, linewidth, x_year_tick_interval | | | ✓ | |
| highlight, ascending, logos→`label_logos` | | | | ✓ (`ys` = `{col: values}`) |

- `y_formatter`: `"compact" | "plain" | "percent" | "norm_max"` (+ decimals →
  `("norm_max", d)`) or a free `"{x:,.0f}"` format string.
- All calls use `show=False, save_path=None` so nothing touches disk.
- `RenderResult(fig, chart)`; `figure_png_bytes(fig, dpi)`;
  `chart_data_xlsx_bytes(chart)` writes `export_data` to a temp file and returns bytes.
- Validation errors (missing x/y column, no numeric y) raise `SpecError` with a
  readable message for the GUI.

Steps:
1. Failing tests: for each of bar/hbar/line/bump the result is a Figure;
   PNG at 500 DPI is exactly 1080 × 1350; **the same spec rendered directly
   via `ElegantChart(...).bar(...)` produces byte-identical PNG** (proves the
   spec adds no styling of its own); switching `chart.type` across all four
   on one spec + df works; `chart_data_xlsx_bytes` round-trips through
   `pd.read_excel`; a missing column raises `SpecError`.
2. Implement. 3. Full suite passes. Commit.

## Task 5 — Streamlit app

**Files:** create `src/elegant_chart/app/{__init__,__main__,studio}.py`,
`tests/test_studio_app.py`; edit `pyproject.toml`.

- Layout: `st.set_page_config(layout="wide")`, `st.columns([1.1, 1.3, 1.2])`.
- **Left (Data):** radio MMA / File; series ID + Fetch button (MMA, result
  cached with `st.cache_data`); `st.file_uploader` (csv/xlsx) + sheet select.
  Reshape steps: list held in `st.session_state.steps`; each step is an
  expander with op-specific widgets, ↑ / ↓ / ✕ buttons; "add step" select +
  button. Failed step shows `st.error` inline, later steps captioned as
  skipped. `st.dataframe` of the reshaped output (head 200).
- **Centre (Preview):** `render()` → `figure_png_bytes(fig, PREVIEW_DPI=220)`
  → `st.image`. Render time shown as a caption. Errors shown as `st.error`
  (never crash).
- **Right (Style):** `st.tabs(["Chart","Text","Layout","Axes","Colors","Legend"])`
  with every field from Task 1. Widget keys are namespaced by spec path
  (`style.text.title`) so values survive chart-type switches (Streamlit keeps
  keyed widget state while the widget is rendered; type-specific widgets
  write into the spec only when visible, and the spec in session state keeps
  their values otherwise). Logo uploads saved to a session temp dir,
  auto-matched to labels by file stem (case-insensitive) and editable in an
  `st.data_editor` label → file table.
- **Download:** `st.download_button` for PNG (500 DPI, rendered on click via a
  callable `data=`) and `chart_data.xlsx`.
- Entry: `elegant-chart-studio` → `streamlit run <path to studio.py>`.

Steps:
1. `AppTest.from_file(studio.py)` smoke test: runs without exception on an
   empty session; with a CSV injected into session state, a preview image is
   produced; switching chart type keeps the title.
2. Implement. 3. Launch headless (`streamlit run … --server.headless true`),
   screenshot with Playwright, check the three panels and the preview.
4. Commit.

## Task 6 — Docs, lint, PR

- README / USAGE: install `pip install -e ".[app]"`, run `elegant-chart-studio`,
  plus the Python `render(ChartSpec(...), df)` example.
- `ruff check` on new files; full `pytest`.
- Push branch, open PR.

## Acceptance check (from spec §1/§4)

- The top-10 airlines chart can be built entirely in the app (file → filter →
  group → sort → top N → hbar + logos).
- Preview ≈ export: same figure, different `savefig` dpi; asserted in tests
  by the 1080 × 1350 check and by byte-equality with the direct library call.
- Existing tests and `examples/*.py` untouched and passing.
- Tweak → preview time measured and shown in the app (target ≤ 1–2 s).
