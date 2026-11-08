# Chart Studio — a GUI for elegant_chart

Date: 2026-11-08
Status: Draft for review

## 1. Intent

Today every chart is produced by editing a Python script, usually by asking
Claude to make a change, re-running, opening the PNG and repeating. Most of
those rounds are small layout nudges: padding, label positions, title
wrapping, legend rows, x-axis ticks. The loop is slow and full of trial and
error.

Chart Studio is a personal, local GUI that lets the owner (a single user)
go from raw data to a finished Elegant Chart PNG without touching code, with
a **live preview** so each tweak takes seconds instead of a round-trip.

Success = a chart like `examples/series_101_top10_airlines.py` (fetch →
filter → group → sum → sort → top 10 → horizontal bar with logos) can be
built entirely in the app, and every layout tweak is visible in the preview
within ~1–2 seconds.

## 2. Goals

1. **Data import** from two sources:
   - MMA Statistics API by series ID (reuse `elegant_chart.get_api_data.get_series_df`,
     including its token resolution and Excel cache).
   - Excel (`.xlsx`) or CSV file upload. For multi-sheet Excel files, pick a sheet.
2. **Data reshaping** as an ordered list of steps the user can add, edit,
   reorder and delete:
   - Filter rows (column, operator `= ≠ > ≥ < ≤ in`, value)
   - Group by + aggregate (sum, mean, count, min, max)
   - Sort (column, ascending/descending)
   - Top N
   - Pivot (long → wide: index column, columns column, values column)
   - A small table preview of the reshaped data is shown under the steps.
3. **Every chart customization the library supports**, exposed as controls.
   No code box or code fallback in the app.
4. **Easy chart-type switching**: changing bar ↔ horizontal bar ↔ line ↔ bump
   keeps the data, the reshaping and all shared style settings. Only
   type-specific controls appear or disappear.
5. **Live preview** rendered by the real matplotlib renderer, so preview and
   exported PNG are the same image (the preview may be downscaled for display).
6. **Download**: the PNG (1080 × 1350 px, 500 DPI) and `chart_data.xlsx`
   (the data actually plotted, using the existing `export_data`).

## 3. Non-goals

- No saving, gallery or reopening of past charts. Make → download → done.
- No multi-user features, logins, hosting or deployment.
- No JavaScript rewrite. The matplotlib renderer stays the single renderer.
- No code editor or "custom Python" step inside the app.
- No new chart types beyond what the library already has (bar, stacked bar,
  horizontal bar, line, bump).

## 4. Anti-goals (would count as failure even if it "works")

- The preview and the exported PNG look different.
- The app changes the established look (fonts, margins, baseline, tick rules
  in `CLAUDE.md`) because it was easier to draw in the GUI.
- The existing Python API and `examples/*.py` scripts break.
- A tweak takes long enough (several seconds or more) that the old
  edit-rerun loop feels no worse.

## 5. Decisions already made

| Decision | Choice | Who decided |
|---|---|---|
| Language | Stay in Python, keep matplotlib renderer | Claude's recommendation, user agreed |
| Users | Single user, personal project, runs locally | User |
| Code fallback | Not needed: the app must cover all customizations | User |
| Data sources | MMA API + Excel/CSV | User |
| Reshaping | In the app | User |
| Layout | **Three panels**: data and reshaping (left), live preview (centre), style tabs (right) | User (option A in mockups) |
| Persistence | None. Settings live only for the session | User |

### Screen layout (option A)

```
┌──────────────┬───────────────────────┬──────────────────────┐
│ DATA         │                       │ STYLE                │
│ ◉ MMA ○ File │                       │ [Chart][Text][Layout]│
│ Series [101] │    Live preview       │ [Axes][Colors]       │
│              │    (4:5 portrait)     │ [Legend]             │
│ RESHAPE      │                       │                      │
│ 1. Filter    │                       │  …controls for the   │
│ 2. Group     │                       │    selected tab…     │
│ 3. Sort      │                       │                      │
│ 4. Top N     │                       │                      │
│ + add step   │                       │ [Download PNG + xlsx]│
│ ┌table─────┐ │                       │                      │
└──────────────┴───────────────────────┴──────────────────────┘
```

Style tabs and what they contain (all map onto existing parameters):

- **Chart**: type (bar / horizontal bar / line / bump), stacked, X column,
  series column(s); type-specific options (markers, linewidth, bar width,
  bump highlight list, ascending, label logos).
- **Text**: title (multi-line), subtitle, caption, x/y labels, annotations
  (list of x, y, text, offset, arrow).
- **Layout**: `x_upper_pad`, `align_x_edges`, `tick_label_pad`,
  `max_label_width` + strategy, logo on/off/custom file, footer on/off,
  y-axis side, y-tick labels inside, show y-axis/spine.
- **Axes**: x/y tick step, max ticks, auto thinning, `x_date_format`,
  `x_minor_ticks`, `x_year_tick_interval`, xlim/ylim, y formatter, value labels.
- **Colors**: theme, per-series color (role name or hex via `color_map`), alpha per series.
- **Legend**: column count (`legend_ncol`). Legend visibility keeps following the
  existing rule (shown only with ≥2 labelled series).

## 6. Architectural direction

### 6.1 The chart spec (Claude's call)

Introduce one plain, serialisable **ChartSpec** object (e.g. nested
dataclasses) that holds everything needed to draw a chart:

```
ChartSpec
├── source:   {kind: "mma", series_id} | {kind: "file", name, sheet}
├── steps:    [ {op: "filter", ...}, {op: "group", ...}, ... ]
├── chart:    {type, x_col, y_cols, type-specific options}
└── style:    {text, layout, axes, colors, legend}   ← mirrors ChartBase args
```

and one function `render(spec, df) -> Figure` that maps it onto `ElegantChart`.

Why: the library currently splits settings between `ElegantChart(...)` and
the `bar()/line()/bump()` call, with several duplicated (`x_tick_step`,
`xlim`, `x_date_format`, …) and `bump()` taking a different data shape. The
GUI should not have to know those quirks. With a spec in the middle:

- GUI widgets map one-to-one onto spec fields.
- Switching chart type = changing `spec.chart.type`. Nothing else is lost.
- Python users get the same benefit: `render(ChartSpec(...))`.

Even without saving charts, the spec is kept in memory for the session and
drives the preview.

### 6.2 Reshaping pipeline

`apply_steps(df, steps) -> df`, a pure function in the library (not in the
GUI), one small pandas operation per step. Errors in a step (e.g. a column
removed upstream) are shown inline on that step. They must not crash the app.

### 6.3 GUI framework (Claude's recommendation; builder may revisit)

**Streamlit**, as a new optional dependency group (`elegant_chart[app]`),
with an entry point (e.g. `elegant-chart-studio` or `python -m elegant_chart.app`).
Reasons: pure Python, built-in file uploader, data-table display, column
layout for the three panels, and image display for the preview. It runs
locally in the browser.

Known risk: Streamlit re-runs the whole script on each change. Rendering at
500 DPI on every keystroke may be slow. Mitigations: render the preview at a
lower DPI (same figsize, so the layout is identical), cache fetched/reshaped
data, and render the full 500 DPI image only on download.

## 7. Constraints

- Canonical output stays 1080 × 1350 px at 500 DPI (`figsize=(2.16, 2.70)`).
- All design rules in `CLAUDE.md` (typography, margins, baseline, ticks,
  legend, colour roles) remain the renderer's responsibility. The app only
  passes parameters.
- The MMA token is read via the existing env var / `TOKEN.txt` logic. It is
  never entered into, displayed or logged by the app.
- Python ≥ 3.12. Existing tests must keep passing, and the existing public API stays
  backward compatible.

## 8. Settled during review (Claude's calls; user may override)

- **Library parameters are not refactored.** The spec layer routes each
  setting to the constructor or the `bar()/line()/bump()` call as the library
  expects today. This follows from the anti-goal that the existing API and
  examples must not break. Any library clean-up is a separate, later task.
- **Logo mapping:** the user uploads one or more image files in the app.
  Each file is auto-matched to a label by file name (case-insensitive,
  ignoring the extension), and the result is shown in an editable
  label → image table so mismatches can be fixed by hand. Uploaded files
  live in a session temp directory, and the spec stores the mapping as
  `{label: temp_path}`, the shape the library already takes. No local folder
  paths, because the app must not depend on the user's file layout.
- **Failed reshape step:** the pipeline stops at the first failing step.
  That step shows its error inline, the steps after it are greyed out, and
  the table and preview show the output of the last step that succeeded.
  No silent skipping, because a skipped filter could produce a wrong-but-plausible chart.

## 9. Left to the builder

- Exact spec field names and module layout (`spec.py`, `pipeline.py`, `app.py`, …).
- Widget choice per parameter (slider vs number input, etc.) and sensible ranges.
- Preview DPI and debounce strategy, as long as the tweak-to-preview time stays ~1–2 s.
