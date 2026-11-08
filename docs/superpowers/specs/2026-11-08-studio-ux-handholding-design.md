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
