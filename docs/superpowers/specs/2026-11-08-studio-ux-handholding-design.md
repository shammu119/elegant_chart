# Chart Studio: hand-held UX (design)

Date: 2026-11-08 · Status: awaiting approval

## Intent
Chart Studio is used by one person (the author), but should still be simple
and very hand-held: someone can build a chart without remembering library
parameter names or format syntax. Principle: **show, don't describe** — any
control that takes a code or technical value shows the result from the
user's own data.

## Goals
- Every format/code field shows a live preview built from the loaded data
  (first example: x date format `%Y`, `%b %y` → "2024", "Mar 24").
- Plain-English labels and a one-line "what this does" on every control.
- Blank/"auto" fields say what auto resolves to for the current data.
- A step checklist in the sidebar (Data → Chart type → Titles → Look →
  Export) that shows progress and names the next thing to do.
- Clear empty states and errors that say how to fix the problem.

## Non-goals / anti-goals
- No second interface or wizard mode.
- No change to chart output (1080×1350 @ 500 DPI) or to the design rules in
  CLAUDE.md.
- No new chart features, no unrelated refactors.
- Hints must never get in the way: they stay collapsible/quiet for repeat use.

## Approaches considered
- **A. Polish existing tabs only** — smallest, but gives no "what next" guidance.
- **B. Polish + guided checklist (chosen)** — A plus the checklist and per-tab
  intro lines; one app, one layout.
- **C. Separate wizard + advanced mode** — most guided, but two UIs to maintain.

## Design (B)
1. **Preview-first inputs** (`app/studio.py`): date format → preset list with
   previews from the data's actual dates + "Custom…" with live preview;
   value format "Custom" → presets (1,234 / 1,234.5 / 12% / $1,234) with a
   preview of a sample value from the data; number fields with auto show
   "auto → <resolved value>".
2. **Plain labels:** rename jargon (e.g. "Op" → "Condition", "N" → "How many
   rows to keep", "Index (x)" → "Rows (x-axis)", "Columns (series)" → "Series
   (one line/bar per…)", "Year tick interval" → "Show a label every _ years").
   Spec field names (`spec.py`) are unchanged.
3. **Help text:** short `help=` or caption on each control; toggles say what
   changes ("Show y spine — draws a vertical line at the axis").
4. **Checklist:** derived purely from the spec/session state (no new state in
   the spec); each step shows done / next / optional.
5. **Empty states and errors:** each says what to do next.
6. A full audit of the Layout, Colors and Legend tabs finalises the list;
   findings are reported before implementation.

## Audit findings (whole app)
Preview-first (show the result before the user commits):
- X date format (text) → presets + live preview from the data's dates.
- Value format "Custom" (`{x:,.0f}`) → presets + preview from a sample value.
- Annotations table: x/y/dx/dy typed blind → click-to-pick x from the data,
  show where it lands; explain dx/dy as "move text right/up (pt)".
- Label text dialog (`\n`) → real multi-line input, preview of the label.
- Logo matching "by file name" → show match status per label.
- Colors: role names (primary…) and hex → swatches of the actual theme colors.
- Theme → mini swatch strip per theme.
- Chart type → tiny icons/thumbnails, not just names.

Plain language / explain-in-place:
- Axes: "X tick step", "Max x ticks", "X minor ticks per interval",
  "Year tick interval (line)", "Auto-thin crowded x labels" → one "X axis
  labels" group with plain wording and "auto → …" shown.
- Layout: "X upper pad (fraction of data span)", "X tick label pad (pt)",
  "Max label width (chars)", "Long labels", "Y tick labels inside the plot",
  "Show y spine" → plain names + a line saying what changes.
- Pipeline steps: "Op", "N", "Index (x)", "Columns (series)", "Aggregate" →
  plain wording; each step type gets a one-line example.
- Series ID (MMA) is a bare number → show the series name after fetching.
- Pipeline "Result" is a table only → say what the chart will use.

Guidance / flow:
- Sidebar checklist (see Design 4); empty states; errors say how to fix.
- Disabled/irrelevant controls are hidden per chart type (already done) →
  add a "why hidden" note where it is not obvious (e.g. bump axes).
- Export: disabled button doesn't say why; no filename control.
- Settings reset: no per-section "reset to auto" button.

## Constraints
- Streamlit only; keep `ChartSpec` serialisable and unchanged.
- Tests (`tests/test_studio_app.py`) must pass; add tests for the preview
  helpers (pure functions, no Streamlit needed).
- ruff format/check clean.

## Next steps
Mockups of three options for the date-format picker and checklist
(design-mockups skill), then you pick; then implementation plan.

## Left to the builder
Exact preset lists, wording of labels, checklist visuals (decided in mockups).
