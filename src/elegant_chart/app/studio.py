# elegant_chart/app/studio.py
"""
Chart Studio — Streamlit script.

Inspector layout: a toolbar (chart type, exports), a sidebar for data and
reshape steps, the chart on a sticky canvas, and an inspector on the right
with one settings section open at a time.  Every widget reads from and
writes to one ``ChartSpec`` kept in ``st.session_state``; the preview is
drawn by :func:`elegant_chart.render` — the real matplotlib renderer — so
preview and download are the same image.

Run with ``elegant-chart-studio`` (or ``streamlit run`` on this file).
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import matplotlib

matplotlib.use("Agg")

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from elegant_chart import sources  # noqa: E402
from elegant_chart.app import ux  # noqa: E402
from elegant_chart.pipeline import apply_step  # noqa: E402
from elegant_chart.pipeline import apply_steps as run_pipeline  # noqa: E402
from elegant_chart.render import (  # noqa: E402
    EXPORT_DPI,
    SpecError,
    chart_data_xlsx_bytes,
    default_x_col,
    figure_png_bytes,
    render,
    resolve_columns,
)
from elegant_chart.spec import (  # noqa: E402
    AGGREGATIONS,
    CHART_TYPE_LABELS,
    CHART_TYPES,
    COLOR_ROLES,
    FILTER_OPERATORS,
    LABEL_WIDTH_STRATEGIES,
    STEP_OPS,
    THEMES,
    Y_FORMATTERS,
    ChartSpec,
    StepSpec,
)

# Same figsize as the export — only the savefig DPI differs (220 → 475 × 594 px).
PREVIEW_DPI = 220
PREVIEW_WIDTH = 440  # css px on the canvas
SIDEBAR_WIDTH = 340  # px, roughly a quarter of a laptop screen
SAMPLE_CSV = Path(__file__).with_name("sample_arrivals.csv")
STEP_LABELS = {
    "filter": "Filter rows",
    "group": "Group + aggregate",
    "sort": "Sort",
    "top_n": "Top N",
    "pivot": "Pivot (long → wide)",
}
IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]


# ── session state ────────────────────────────────────────────────────────────


def _state() -> Any:
    ss = st.session_state
    if "spec" not in ss:
        ss.spec = ChartSpec()
        ss.step_ids = []
        ss.raw_df = None
        ss.raw_key = None
        ss.load_error = None
        ss.tmpdir = tempfile.mkdtemp(prefix="chart_studio_")
        ss.preview_cache = {}
    return ss


def _spec() -> ChartSpec:
    return st.session_state.spec


# ── cached loaders ───────────────────────────────────────────────────────────


@st.cache_data(show_spinner="Fetching series…")
def _cached_mma(series_id: int) -> pd.DataFrame:
    return sources.load_mma_series(series_id)


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_mma_info(series_id: int) -> dict:
    return sources.load_mma_info(series_id)


@st.cache_data(show_spinner=False)
def _cached_sheets(data: bytes) -> list[str]:
    return sources.list_sheets(data)


@st.cache_data(show_spinner=False)
def _cached_upload(data: bytes, name: str, sheet: Optional[str]) -> pd.DataFrame:
    return sources.read_uploaded(data, name, sheet)


# ── small widget helpers (value from spec → widget → back into spec) ─────────


def _opt_number(
    label: str,
    value: Any,
    key: str,
    *,
    step: float = 1.0,
    integer: bool = False,
    min_value: Optional[float] = None,
    help: Optional[str] = None,
) -> Any:
    """Number input where an empty field means ``None`` (= library auto)."""
    if integer:
        v = st.number_input(
            label,
            value=None if value is None else int(value),
            step=int(step),
            min_value=None if min_value is None else int(min_value),
            key=key,
            placeholder="auto",
            help=help,
        )
        return None if v is None else int(v)
    v = st.number_input(
        label,
        value=None if value is None else float(value),
        step=float(step),
        min_value=min_value,
        key=key,
        placeholder="auto",
        format="%g",
        help=help,
    )
    return None if v is None else float(v)


def _select(
    label: str,
    options: Sequence[Any],
    value: Any,
    key: str,
    fmt: Optional[Callable[[Any], str]] = None,
    keep_missing: bool = False,
    **kw: Any,
) -> Any:
    options = list(options)
    if keep_missing and value not in (None, "") and value not in options:
        # A column removed upstream stays selected (and flagged) instead of
        # silently switching to another column — the step then fails visibly.
        options = [value, *options]
        base = fmt or (lambda o: str(o))
        fmt = lambda o, _v=value, _b=base: f"⚠ {_b(o)} (missing)" if o == _v else _b(o)  # noqa: E731
    index = options.index(value) if value in options else 0
    if not options:
        st.selectbox(label, ["—"], key=key, disabled=True)
        return None
    return st.selectbox(
        label, options, index=index, key=key, format_func=fmt or (lambda o: str(o)), **kw
    )


def _range(label: str, value: Optional[tuple], key: str) -> Optional[tuple]:
    c1, c2 = st.columns(2)
    lo = c1.number_input(
        f"{label} min",
        value=None if value is None else float(value[0]),
        key=f"{key}.lo",
        placeholder="auto",
        format="%g",
    )
    hi = c2.number_input(
        f"{label} max",
        value=None if value is None else float(value[1]),
        key=f"{key}.hi",
        placeholder="auto",
        format="%g",
    )
    if lo is None or hi is None:
        return None
    return (float(lo), float(hi))


def _save_upload(f: Any) -> str:
    """Save an uploaded file into the session temp dir; return its path."""
    ss = st.session_state
    digest = hashlib.sha1(f.getvalue()).hexdigest()[:10]
    path = os.path.join(ss.tmpdir, f"{digest}_{os.path.basename(f.name)}")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(f.getvalue())
    return path


# ── left panel: data + reshape ───────────────────────────────────────────────


def _group(label: str) -> None:
    """Small uppercase group label (SOURCE, STEPS, …) in place of big headings."""
    st.markdown(f'<div class="ec-gh">{label}</div>', unsafe_allow_html=True)


def _segmented(
    label: str,
    options: Sequence[Any],
    value: Any,
    key: str,
    fmt: Optional[Callable[[Any], str]] = None,
    **kw: Any,
) -> Any:
    """Single-choice segmented control that can't be left empty.

    The spec value seeds the widget only on first draw; after that the widget's
    own state wins (so callbacks can set ``st.session_state[key]`` safely).
    """
    options = list(options)
    if key not in st.session_state:
        kw["default"] = value if value in options else options[0]
    out = st.segmented_control(
        label, options, key=key, required=True, format_func=fmt or (lambda o: str(o)), **kw
    )
    return out if out is not None else (value if value in options else options[0])


def progress_rail(df: Optional[pd.DataFrame]) -> None:
    """Five-step checklist at the top of the sidebar; names the next thing to do."""
    spec = _spec()
    ch = spec.chart
    items = ux.checklist(
        has_data=df is not None and not df.empty,
        chart_ready=bool(df is not None and ch.x_col in df.columns and ch.y_cols),
        has_title=bool((spec.style.text.title or "").strip()),
    )
    rows = []
    for i, it in enumerate(items, 1):
        badge = "✓" if it.state == "done" else str(i)
        rows.append(
            f'<div class="ec-step {it.state}"><span class="ec-badge">{badge}</span>'
            f"<div><b>{_esc(it.label)}{' · optional' if it.state == 'optional' else ''}</b>"
            f"<small>{_esc(it.hint)}</small></div></div>"
        )
    st.markdown(f'<div class="ec-rail">{"".join(rows)}</div>', unsafe_allow_html=True)


def data_panel() -> Optional[pd.DataFrame]:
    ss, spec = st.session_state, _spec()
    _group("Source")
    kind = _segmented(
        "Source",
        ["mma", "file"],
        spec.source.kind if spec.source.kind in ("mma", "file") else "mma",
        "source.kind",
        fmt=lambda k: "MMA series" if k == "mma" else "File",
        label_visibility="collapsed",
        width="stretch",
    )
    spec.source.kind = kind

    if kind == "mma":
        c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
        sid = c1.number_input(
            "Series ID",
            min_value=1,
            step=1,
            key="source.series_id",
            value=spec.source.series_id or 101,
        )
        if c2.button("Fetch", width="stretch"):
            spec.source.series_id = int(sid)
            try:
                ss.raw_df = _cached_mma(int(sid))
                ss.raw_key = f"mma:{int(sid)}"
                ss.source_label = f"MMA series {int(sid)}"
                ss.series_info = _cached_mma_info(int(sid))
                ss.load_error = None
            except Exception as exc:  # noqa: BLE001 — shown to the user, never crashes the app
                ss.load_error = str(exc)
    else:
        up = st.file_uploader(
            "Upload .xlsx or .csv",
            type=["xlsx", "xlsm", "csv"],
            key="source.upload",
            label_visibility="collapsed",
        )
        if up is not None:
            data = up.getvalue()
            sheet = None
            try:
                if sources.is_excel(up.name):
                    sheets = _cached_sheets(data)
                    sheet = _select("Sheet", sheets, spec.source.sheet, "source.sheet")
                key = f"file:{hashlib.sha1(data).hexdigest()}:{sheet}"
                if ss.raw_key != key:
                    ss.raw_df = _cached_upload(data, up.name, sheet)
                    ss.raw_key = key
                    ss.load_error = None
                ss.source_label = up.name if sheet is None else f"{up.name} · {sheet}"
                spec.source.name, spec.source.sheet = up.name, sheet
            except Exception as exc:  # noqa: BLE001
                ss.load_error = str(exc)

    if ss.load_error:
        st.error(ss.load_error)
    raw = ss.raw_df
    if raw is None:
        st.caption("Load a series or a file to start.")
        return None
    name = ss.get("source_label") or "Loaded data"
    info = ss.get("series_info") if str(ss.get("raw_key", "")).startswith("mma:") else None
    if info and info.get("name"):
        name = str(info["name"])
    st.markdown(
        f'<div class="ec-file"><span>{_esc(name)}</span>'
        f"<em>{len(raw):,} rows × {len(raw.columns)} cols</em></div>",
        unsafe_allow_html=True,
    )
    if info and info.get("name"):
        extra = [str(info[k]) for k in ("frequency", "unit") if info.get(k)]
        st.caption(" · ".join([ss.source_label, *extra]))

    _group("Steps")
    _sync_steps_from_widgets(spec.steps, ss.step_ids)
    run = _pipeline(raw, spec.steps)
    for i, step in enumerate(list(spec.steps)):
        sid = ss.step_ids[i]
        res = run.results[i]
        label = f"{i + 1}  ·  {_step_summary(step)}"
        if res.status == "ok":
            label += f"  —  {res.rows:,} rows"
        elif res.status == "error":
            label += "  —  ⚠ error"
        else:
            label += "  —  skipped"
        open_now = res.status == "error" or ss.get("open_step") == sid
        with st.expander(label, expanded=open_now, key=f"step.{sid}.exp"):
            if res.status == "skipped":
                st.caption("Skipped: an earlier step failed.")
            _step_controls(i, step, sid, run.columns_in[i])
            if res.status == "error":
                st.error(res.error)
    with st.popover("＋ Add step", type="tertiary"):
        for op in STEP_OPS:
            st.button(
                STEP_LABELS.get(op, op),
                key=f"add_step.{op}",
                on_click=_add_step,
                args=(op,),
                type="tertiary",
            )

    _group("Result")
    result = run.df
    st.dataframe(result.head(200), height=240, width="stretch", hide_index=True)
    if len(result) > 200:
        st.caption(f"Showing 200 of {len(result):,} rows")
    return result


def _esc(text: Any) -> str:
    import html  # noqa: PLC0415

    return html.escape(str(text))


# Widget key suffix → step param, per op (see ``_step_controls``).
_STEP_WIDGET_PARAMS = {
    "filter": {"column": "column", "op": "operator", "value": "value"},
    "group": {"by": "by", "agg": "agg", "columns": "columns"},
    "sort": {"column": "column", "asc": "ascending"},
    "top_n": {"n": "n"},
    "pivot": {"index": "index", "columns": "columns", "values": "values"},
}


def _sync_steps_from_widgets(steps: list, step_ids: list) -> None:
    """Copy this run's widget values into the step params *before* drawing.

    The step rows show a summary and a row count in their (collapsed) header,
    which is drawn before the step's own widgets.  Reading the widget state
    first keeps that header current instead of one interaction behind.
    """
    ss = st.session_state
    for step, sid in zip(steps, step_ids):
        for suffix, param in _STEP_WIDGET_PARAMS.get(step.op, {}).items():
            key = f"step.{sid}.{suffix}"
            if key in ss:
                val = ss[key]
                step.params[param] = int(val) if param == "n" and val is not None else val


@dataclass
class _PipelineRun:
    df: pd.DataFrame
    results: list  # pipeline.StepResult per step
    columns_in: list  # input columns of each step (for the step's column pickers)


def _pipeline(raw: pd.DataFrame, steps: list) -> _PipelineRun:
    """Run the reshape steps, memoised on (data, steps).

    Style edits rerun the whole script; this keeps them from re-running the
    pandas pipeline when neither the data nor the steps changed.
    """
    ss = st.session_state
    key = json.dumps(
        [ss.get("raw_key"), [[s.op, s.params] for s in steps]], sort_keys=True, default=str
    )
    memo = ss.get("pipeline_memo")
    if memo and memo[0] == key:
        return memo[1]
    cols_in, current, failed = [], raw, False
    for step in steps:
        cols_in.append(list(current.columns))
        if failed:
            continue
        try:
            current = apply_step(current, step.op, step.params)
        except Exception:  # noqa: BLE001 — reported by run_pipeline below
            failed = True
    result = run_pipeline(raw, steps)  # the library pipeline is the source of truth
    run = _PipelineRun(result.df, result.steps, cols_in)
    ss.pipeline_memo = (key, run)
    return run


def _step_summary(step: StepSpec) -> str:
    p = step.params
    try:
        if step.op == "filter" and p.get("column") is not None:
            return f"Filter · {p['column']} {p.get('operator', '=')} {p.get('value') or '…'}"
        if step.op == "group" and p.get("by"):
            return f"Group · {', '.join(map(str, p['by']))} · {p.get('agg', 'sum')}"
        if step.op == "sort" and p.get("column") is not None:
            return f"Sort · {p['column']} {'↑' if p.get('ascending') else '↓'}"
        if step.op == "top_n":
            return f"Top {int(p.get('n', 10))}"
        if step.op == "pivot" and p.get("index") is not None:
            return f"Pivot · {p['index']} × {p.get('columns')}"
    except Exception:  # noqa: BLE001 — a summary must never break the panel
        pass
    return STEP_LABELS.get(step.op, step.op)


def _add_step(op: str) -> None:
    ss = st.session_state
    defaults = {
        "filter": {"operator": "="},
        "group": {"agg": "sum"},
        "sort": {"ascending": False},
        "top_n": {"n": 10},
        "pivot": {},
    }
    ss.spec.steps.append(StepSpec(op, dict(defaults.get(op, {}))))
    ss.step_ids.append(uuid.uuid4().hex[:8])
    ss.open_step = ss.step_ids[-1]  # a new step opens so it can be set up


def _move_step(i: int, delta: int) -> None:
    ss = st.session_state
    j = i + delta
    if 0 <= j < len(ss.spec.steps):
        for lst in (ss.spec.steps, ss.step_ids):
            lst[i], lst[j] = lst[j], lst[i]


def _delete_step(i: int) -> None:
    ss = st.session_state
    del ss.spec.steps[i]
    del ss.step_ids[i]


def _step_controls(i: int, step: StepSpec, sid: str, cols: list) -> None:
    p, k = step.params, f"step.{sid}"
    if step.op == "filter":
        c1, c2 = st.columns([3, 1])
        with c1:
            p["column"] = _select("Column", cols, p.get("column"), f"{k}.column", keep_missing=True)
        with c2:
            p["operator"] = _select("Op", FILTER_OPERATORS, p.get("operator", "="), f"{k}.op")
        hint = " (comma-separated)" if p["operator"] == "in" else ""
        p["value"] = st.text_input(
            f"Value{hint}", value=str(p.get("value") or ""), key=f"{k}.value"
        )
    elif step.op == "group":
        by_prev = list(p.get("by") or [])
        by_opts = cols + [c for c in by_prev if c not in cols]  # keep missing ones visible
        p["by"] = st.multiselect("Group by", by_opts, default=by_prev, key=f"{k}.by")
        p["agg"] = _select("Aggregate", AGGREGATIONS, p.get("agg", "sum"), f"{k}.agg")
        val_prev = [c for c in p.get("columns") or [] if c not in p["by"]]
        val_opts = [c for c in cols if c not in p["by"]]
        val_opts += [c for c in val_prev if c not in val_opts]
        p["columns"] = st.multiselect(
            "Value columns (empty = all numeric)", val_opts, default=val_prev, key=f"{k}.columns"
        )
    elif step.op == "sort":
        p["column"] = _select("Column", cols, p.get("column"), f"{k}.column", keep_missing=True)
        p["ascending"] = st.toggle("Ascending", value=bool(p.get("ascending")), key=f"{k}.asc")
    elif step.op == "top_n":
        p["n"] = int(
            st.number_input("N", min_value=0, step=1, value=int(p.get("n", 10)), key=f"{k}.n")
        )
    elif step.op == "pivot":
        p["index"] = _select("Index (x)", cols, p.get("index"), f"{k}.index", keep_missing=True)
        p["columns"] = _select(
            "Columns (series)", cols, p.get("columns"), f"{k}.columns", keep_missing=True
        )
        p["values"] = _select("Values", cols, p.get("values"), f"{k}.values", keep_missing=True)
    b1, b2, b3, _ = st.columns([1, 1, 1, 3])
    b1.button("↑", key=f"{k}.up", on_click=_move_step, args=(i, -1), help="Move up")
    b2.button("↓", key=f"{k}.down", on_click=_move_step, args=(i, 1), help="Move down")
    b3.button("✕", key=f"{k}.del", on_click=_delete_step, args=(i,), help="Delete step")


# ── right panel: style tabs ──────────────────────────────────────────────────


INSPECTOR_SECTIONS = ["Chart", "Text", "Axes", "Colors", "More"]
INSPECTOR_LABELS = {"More": "…"}  # Layout + legend live under "…"


def inspector_panel(df: Optional[pd.DataFrame]) -> None:
    """Right-hand inspector: one section at a time, picked by a segmented control.

    Only the open section's widgets are drawn, which keeps each rerun light.
    Every widget is seeded from the spec, so switching sections loses nothing.
    """
    spec = _spec()
    section = _segmented(
        "Inspector",
        INSPECTOR_SECTIONS,
        "Chart",
        "inspector.section",
        fmt=lambda o: INSPECTOR_LABELS.get(o, o),
        label_visibility="collapsed",
        width="stretch",
    )
    if section == "Chart":
        chart_tab(spec, df)
    elif section == "Text":
        text_tab(spec)
    elif section == "Axes":
        axes_tab(spec, df)
    elif section == "Colors":
        colors_tab(spec, df)
    else:
        _group("Layout")
        layout_tab(spec)
        _group("Legend")
        st.caption("A legend is drawn only when two or more series are plotted.")
        spec.style.legend.legend_ncol = _opt_number(
            "Legend columns",
            spec.style.legend.legend_ncol,
            "style.legend.ncol",
            integer=True,
            min_value=1,
            help="Empty = min(3, number of series)",
        )


def chart_type_control() -> None:
    """Chart type, drawn in the toolbar."""
    ch = _spec().chart
    ch.type = _segmented(
        "Chart type",
        CHART_TYPES,
        ch.type,
        "chart.type",
        fmt={"bar": "Bar", "hbar": "H-bar", "line": "Line", "bump": "Bump"}.get,
        label_visibility="collapsed",
        help=" · ".join(CHART_TYPE_LABELS[t] for t in CHART_TYPES),
    )


def chart_tab(spec: ChartSpec, df: Optional[pd.DataFrame]) -> None:
    ch = spec.chart
    if df is not None and not df.empty:
        cols = list(df.columns)
        ss = st.session_state
        if ss.get("chart_cols") != cols:
            # The reshaped data changed shape: re-pick sensible defaults rather
            # than keep pointing at a column whose meaning changed (e.g. a summed Year).
            if ss.get("chart_cols") is not None or ch.x_col not in cols:
                ch.x_col = default_x_col(df)
                ch.y_cols = [c for c in ch.y_cols if c in cols and c != ch.x_col]
                for key in ("chart.x_col", "chart.y_cols"):
                    ss.pop(key, None)
            ss.chart_cols = cols
        ch.x_col = _select("X column", cols, ch.x_col, "chart.x_col")
        numeric = [c for c in df.select_dtypes("number").columns if c != ch.x_col]
        ch.y_cols = st.multiselect(
            "Series",
            numeric,
            default=[c for c in ch.y_cols if c in numeric] or numeric,
            key="chart.y_cols",
        )
    else:
        st.caption("Load data to choose columns.")

    if ch.type in ("bar", "hbar", "line"):
        ch.show_value_labels = st.toggle(
            "Value labels", ch.show_value_labels, key="chart.show_value_labels"
        )
    if ch.type == "line":
        ch.markers = st.toggle("Markers", ch.markers, key="chart.markers")
    if ch.type in ("bar", "line"):
        ch.compact_years = st.toggle(
            "Compact years ('21)", ch.compact_years, key="chart.compact_years"
        )
    if ch.type == "line":
        ch.linewidth = _opt_number(
            "Line width (pt)", ch.linewidth, "chart.linewidth", step=0.1, min_value=0.0
        )
    if ch.type == "bar":
        ch.stacked = st.toggle("Stacked", ch.stacked, key="chart.stacked")
    if ch.type in ("bar", "hbar"):
        ch.bar_width = _opt_number(
            "Bar width", ch.bar_width, "chart.bar_width", step=0.05, min_value=0.0
        )
    if ch.type in ("bar", "line"):
        ch.rotation = st.number_input(
            "X label rotation",
            value=float(ch.rotation),
            step=15.0,
            key="chart.rotation",
            format="%g",
        )
    if ch.type == "bump":
        series = list(ch.y_cols) if ch.y_cols else []
        ch.highlight = st.multiselect(
            "Highlight (empty = all)",
            series,
            default=[s for s in ch.highlight if s in series],
            key="chart.highlight",
        )
        ch.ascending = st.toggle("Smallest value = rank 1", ch.ascending, key="chart.ascending")
        bump_style_controls(ch, series)
    if ch.type in ("hbar", "bump"):
        logos_editor(spec, df)


def bump_style_controls(ch: Any, series: list) -> None:
    """Ghost-line colour/opacity, line widths and label text for bump charts."""
    _group("Lines")
    c1, c2 = st.columns(2)
    with c1:
        ch.hero_linewidth = _opt_number(
            "Highlighted line width (pt)",
            ch.hero_linewidth,
            "chart.hero_lw",
            step=0.1,
            min_value=0.0,
        )
    with c2:
        ch.other_linewidth = _opt_number(
            "Other line width (pt)",
            ch.other_linewidth,
            "chart.other_lw",
            step=0.1,
            min_value=0.0,
        )
    c1, c2 = st.columns([1, 2], vertical_alignment="bottom")
    ch.other_color = c1.color_picker("Other lines colour", ch.other_color, key="chart.other_color")
    ch.other_alpha = c2.slider(
        "Other lines opacity", 0.0, 1.0, float(ch.other_alpha), 0.05, key="chart.other_alpha"
    )
    if not series:
        return
    n = len(ch.label_display)
    if st.button(
        f"Edit label text…{f'  ({n} set)' if n else ''}", key="chart.label_dialog", width="stretch"
    ):
        _label_text_dialog(series)


@st.dialog("Label text")
def _label_text_dialog(series: list) -> None:
    """Long per-series label table, in a dialog so it doesn't stretch the inspector."""
    ch = _spec().chart
    st.caption("Leave blank to use the series name. Type `\\n` for a line break.")
    rows = [
        {"series": s, "label": ch.label_display.get(s, "").replace("\n", "\\n")} for s in series
    ]
    edited = st.data_editor(
        pd.DataFrame(rows, columns=["series", "label"]).astype({"label": "string"}),
        hide_index=True,
        width="stretch",
        disabled=["series"],
        key="chart.label_display",
    )
    ch.label_display = {
        r["series"]: str(r["label"]).replace("\\n", "\n")
        for r in edited.to_dict("records")
        if r.get("label") is not None and not pd.isna(r["label"]) and str(r["label"]).strip()
    }
    if st.button("Done", type="primary"):
        st.rerun()


def logos_editor(spec: ChartSpec, df: Optional[pd.DataFrame]) -> None:
    ch = spec.chart
    if df is None or df.empty or ch.x_col not in df.columns:
        return
    labels = (
        [str(v) for v in df[ch.x_col].tolist()]
        if ch.type == "hbar"
        else [str(c) for c in ch.y_cols]
    )
    _group("Label logos")
    files = st.file_uploader(
        "Logo images (matched to labels by file name)",
        type=IMAGE_TYPES,
        accept_multiple_files=True,
        key="chart.logo_files",
    )
    paths = {f.name: _save_upload(f) for f in files or []}
    by_stem = {os.path.splitext(n)[0].lower(): n for n in paths}
    current = {lbl: os.path.basename(p).split("_", 1)[-1] for lbl, p in ch.logos.items()}
    rows = []
    for lbl in labels:
        name = current.get(lbl) or by_stem.get(lbl.lower(), "")
        rows.append({"label": lbl, "image": name if name in paths else ""})
    if not paths:
        ch.logos = {}
        return
    edited = st.data_editor(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        key="chart.logo_table",
        disabled=["label"],
        column_config={
            "image": st.column_config.SelectboxColumn("Image", options=[""] + sorted(paths))
        },
    )
    ch.logos = {
        r["label"]: paths[r["image"]]
        for r in edited.to_dict("records")
        if r.get("image") and r["image"] in paths
    }


def text_tab(spec: ChartSpec) -> None:
    t = spec.style.text
    t.title = (
        st.text_area("Title (Enter for a new line)", t.title or "", height=68, key="text.title")
        or None
    )
    t.subtitle = st.text_input("Subtitle", t.subtitle or "", key="text.subtitle") or None
    t.caption = (
        st.text_area("Caption / source", t.caption or "", height=68, key="text.caption") or None
    )
    c1, c2 = st.columns(2)
    t.xlabel = c1.text_input("X label", t.xlabel or "", key="text.xlabel") or None
    t.ylabel = c2.text_input("Y label", t.ylabel or "", key="text.ylabel") or None
    _group("Annotations")
    st.caption(
        "x: a year, number, date (2021-06-30) or category name. dx/dy: text offset in points."
    )
    base = pd.DataFrame(
        t.annotations or [], columns=["x", "y", "text", "dx", "dy", "arrow"]
    ).astype(
        {
            "x": "string",
            "text": "string",
            "y": "float",
            "dx": "float",
            "dy": "float",
            "arrow": "boolean",
        }
    )
    edited = st.data_editor(
        base,
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key="text.annotations",
        column_config={"arrow": st.column_config.CheckboxColumn("arrow")},
    )
    anns = []
    for r in edited.to_dict("records"):
        r = {k: v for k, v in r.items() if v is not None and not pd.isna(v)}
        if r.get("text") and "x" in r and "y" in r:
            anns.append(r)
    t.annotations = anns


def layout_tab(spec: ChartSpec) -> None:
    lay = spec.style.layout
    lay.x_upper_pad = _opt_number(
        "X upper pad (fraction of data span)",
        lay.x_upper_pad,
        "layout.x_upper_pad",
        step=0.01,
        min_value=0.0,
    )
    lay.align_x_edges = st.toggle(
        "Pad x edges so end labels stay centred", lay.align_x_edges, key="layout.align_x_edges"
    )
    lay.tick_label_pad = _opt_number(
        "X tick label pad (pt)", lay.tick_label_pad, "layout.tick_label_pad", step=0.5
    )
    c1, c2 = st.columns(2)
    with c1:
        lay.max_label_width = _opt_number(
            "Max label width (chars)",
            lay.max_label_width,
            "layout.max_label_width",
            integer=True,
            min_value=1,
        )
    with c2:
        lay.label_width_strategy = _select(
            "Long labels", LABEL_WIDTH_STRATEGIES, lay.label_width_strategy, "layout.label_strategy"
        )
    st.divider()
    lay.show_footer = st.toggle(
        "Footer (rule, caption, logo)", lay.show_footer, key="layout.show_footer"
    )
    lay.logo_mode = st.radio(
        "Footer logo",
        ["default", "none", "custom"],
        horizontal=True,
        index=["default", "none", "custom"].index(lay.logo_mode),
        key="layout.logo_mode",
        format_func={"default": "Bundled", "none": "Off", "custom": "Custom"}.get,
    )
    if lay.logo_mode == "custom":
        f = st.file_uploader("Logo image", type=IMAGE_TYPES, key="layout.logo_file")
        if f is not None:
            lay.logo_path = _save_upload(f)
        if not lay.logo_path:
            st.caption("No image yet — the bundled logo is used.")
    st.divider()
    lay.y_axis_side = st.radio(
        "Y-axis side",
        ["right", "left"],
        horizontal=True,
        index=0 if lay.y_axis_side == "right" else 1,
        key="layout.y_axis_side",
    )
    lay.y_tick_labels_inside = st.toggle(
        "Y tick labels inside the plot", lay.y_tick_labels_inside, key="layout.y_inside"
    )
    lay.show_y_axis = st.toggle(
        "Show y gridlines + labels", lay.show_y_axis, key="layout.show_y_axis"
    )
    lay.show_y_spine = st.toggle("Show y spine", lay.show_y_spine, key="layout.show_y_spine")


def _y_sample(spec: ChartSpec, df: Optional[pd.DataFrame]) -> float:
    """Largest plotted value — the number the format previews are drawn from."""
    if df is not None and not df.empty:
        cols = [c for c in spec.chart.y_cols if c in df.columns]
        try:
            top = float(df[cols].max().max()) if cols else float("nan")
        except (TypeError, ValueError):
            top = float("nan")
        if top == top and top != 0:  # not NaN, not zero
            return top
    return 12345.0


def _axis_strip(labels: list[str]) -> None:
    """Mini x-axis showing the labels a format will print."""
    n = len(labels)
    ticks = "".join(
        f'<i style="left:{(i * 100 / (n - 1) if n > 1 else 0):.1f}%"></i>'
        f'<em style="left:{(i * 100 / (n - 1) if n > 1 else 0):.1f}%">{_esc(t)}</em>'
        for i, t in enumerate(labels)
    )
    st.markdown(
        '<div class="ec-strip"><span>Your axis will read</span>'
        f'<div class="ec-axis">{ticks}</div></div>',
        unsafe_allow_html=True,
    )


def _date_format_picker(a: Any, df: Optional[pd.DataFrame], x_col: Optional[str]) -> None:
    """Pick an x-label date style by what it prints, not by its code."""
    dates = None
    if df is not None and x_col in (df.columns if df is not None else []):
        dates = ux.sample_dates(df[x_col].tolist())
    if dates is None:
        st.caption(
            "X values here are names or numbers, not dates, so no date format is needed."
            if df is not None
            else "Load data to see what your x labels will look like."
        )
        return
    auto = "auto"
    presets = [c for c, _ in ux.DATE_PRESETS]
    current = a.x_date_format
    state_key = "axes.x_date_style"
    if state_key not in st.session_state:
        st.session_state[state_key] = (
            auto if not current else (current if current in presets else "custom")
        )
    names = dict(ux.DATE_PRESETS)

    def _label(code: str) -> str:
        if code == auto:
            return "Automatic — the chart picks a style that suits your data"
        if code == "custom":
            return "Custom… (type your own code)"
        labels = ux.date_label_preview(code, dates).labels
        return f"**{labels[0]} … {labels[-1]}**  ·  {names[code]}  `{code}`"

    choice = st.radio(
        "Date style",
        [auto, *presets, "custom"],
        key=state_key,
        format_func=_label,
        help="Pick the style that reads the way you want. The result is drawn from your own dates.",
    )
    if choice == auto:
        a.x_date_format = None
        return
    if choice == "custom":
        code = st.text_input(
            "Your date code",
            value=current if current and current not in presets else "%b %Y",
            key="axes.x_date_format",
            help="Codes: %Y 2024 · %y 24 · %b Jan · %B January · %m 01 · %d 05",
        )
    else:
        code = choice
    preview = ux.date_label_preview(code, dates)
    if preview.problem:
        st.warning(preview.problem, icon=":material/info:")
    if preview.labels:
        _axis_strip(preview.labels)
        a.x_date_format = code
    else:
        a.x_date_format = None


def _value_format_picker(a: Any, sample: float) -> None:
    """Pick the number style by what it prints for the largest value."""
    r = lambda style, x=sample, **kw: ux.format_value(style, x, **kw)  # noqa: E731
    dec = int(a.y_formatter_decimals)
    labels = {
        "compact": f"**{r('compact')}**  ·  Compact",
        "plain": f"**{r('plain')}**  ·  Plain",
        "percent": "**10%**  ·  Percent (0.1 becomes 10%)",
        "norm_max": (
            f"**{r('norm_max', sample / 2, decimals=dec, max_value=sample)}**"
            "  ·  Share of the largest value (half of it shown)"
        ),
        "custom": "Custom… (type your own format)",
    }
    st.caption(f"Previews use your largest value, {sample:,.0f}.")
    a.y_formatter = st.radio(
        "Number style",
        list(Y_FORMATTERS),
        index=list(Y_FORMATTERS).index(a.y_formatter) if a.y_formatter in Y_FORMATTERS else 0,
        key="axes.y_formatter",
        format_func=lambda k: labels.get(k, k),
    )
    if a.y_formatter == "norm_max":
        a.y_formatter_decimals = int(
            st.number_input("Decimals", 0, 6, int(a.y_formatter_decimals), key="axes.y_decimals")
        )
    if a.y_formatter == "custom":
        a.y_formatter_custom = st.text_input(
            "Your number format",
            a.y_formatter_custom,
            key="axes.y_custom",
            help="Python format. {x:,.0f} gives 298,835 · {x:,.1f} gives 298,835.0",
        )
        problem = ux.value_style_problem(a.y_formatter_custom)
        if problem:
            st.warning(problem, icon=":material/info:")
        else:
            st.caption(
                "Result: "
                + "  ·  ".join(
                    ux.format_value("custom", v, custom=a.y_formatter_custom) or ""
                    for v in (sample, sample / 20, sample / 60)
                )
            )


def axes_tab(spec: ChartSpec, df: Optional[pd.DataFrame] = None) -> None:
    a, ctype = spec.style.axes, spec.chart.type
    if ctype == "bump":
        st.caption("Bump charts place their own rank axis; these settings don't apply.")
    _group("X-axis labels")
    if ctype in ("bar", "line"):
        _date_format_picker(a, df, spec.chart.x_col)
    c1, c2 = st.columns(2)
    with c1:
        a.x_tick_step = _opt_number(
            "Label every…",
            a.x_tick_step,
            "axes.x_tick_step",
            help="Gap between x labels in x units (2 = every second year). Blank = automatic.",
        )
        a.x_minor_ticks = _opt_number(
            "Small ticks between labels",
            a.x_minor_ticks,
            "axes.x_minor_ticks",
            integer=True,
            min_value=0,
            help="1 puts a single small tick halfway between labels. Blank = none.",
        )
    with c2:
        a.max_x_ticks = _opt_number(
            "Most labels to show",
            a.max_x_ticks,
            "axes.max_x_ticks",
            integer=True,
            min_value=1,
            help="Caps how many x labels are drawn. Blank = automatic.",
        )
        a.x_year_tick_interval = _opt_number(
            "Label every… years (line)",
            a.x_year_tick_interval,
            "axes.x_year_tick_interval",
            integer=True,
            min_value=1,
            help="For line charts with dates: one label every N years. Blank = automatic.",
        )
    a.auto_x_thinning = st.toggle(
        "Skip labels when they get crowded",
        a.auto_x_thinning,
        key="axes.auto_x_thinning",
        help="Drops some x labels when they would overlap, instead of squeezing them.",
    )
    a.xlim = _range("X", a.xlim, "axes.xlim")
    _group("Y-axis")
    c1, c2 = st.columns(2)
    with c1:
        a.y_tick_step = _opt_number(
            "Gridline every…",
            a.y_tick_step,
            "axes.y_tick_step",
            help="Gap between horizontal gridlines, in value units. Blank = automatic.",
        )
    with c2:
        a.max_y_ticks = _opt_number(
            "Most gridlines",
            a.max_y_ticks,
            "axes.max_y_ticks",
            integer=True,
            min_value=1,
            help="Caps how many y labels are drawn. Blank = automatic.",
        )
    a.ylim = _range("Y", a.ylim, "axes.ylim")
    _group("Value labels")
    _value_format_picker(a, _y_sample(spec, df))


def colors_tab(spec: ChartSpec, df: Optional[pd.DataFrame]) -> None:
    c = spec.style.colors
    c.theme = _select("Theme", THEMES, c.theme, "colors.theme")
    labels: list[str] = []
    if df is not None and not df.empty:
        try:
            labels = [str(s) for s in resolve_columns(spec, df)[1]]
        except SpecError:
            labels = []
    if not labels:
        st.caption("Per-series colours appear once series are chosen.")
        return
    options = ["auto", *COLOR_ROLES, "custom"]
    new_map: dict[str, str] = {}
    new_alpha: dict[str, float] = {}
    _group("Series")
    for lbl in labels:
        cur = c.color_map.get(lbl)
        choice = "auto" if cur is None else (cur if cur in COLOR_ROLES else "custom")
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        with c1:
            choice = _select(lbl, options, choice, f"colors.role.{lbl}")
        if choice == "custom":
            new_map[lbl] = c2.color_picker(
                "Hex", cur if cur and cur.startswith("#") else "#64D2FF", key=f"colors.hex.{lbl}"
            )
        elif choice != "auto":
            new_map[lbl] = choice
        if spec.chart.type != "bump":
            alpha = st.slider(
                "Opacity",
                0.0,
                1.0,
                float(c.alpha_map.get(lbl, 1.0)),
                0.05,
                key=f"colors.alpha.{lbl}",
                label_visibility="collapsed",
                format="%.2f opacity",
            )
            if alpha < 1.0:
                new_alpha[lbl] = alpha
    c.color_map, c.alpha_map = new_map, new_alpha


# ── centre: canvas + exports ─────────────────────────────────────────────────


def canvas_panel(df: Optional[pd.DataFrame]) -> None:
    """The chart on a neutral stage.  Sticky on wide screens (see ``_CSS``)."""
    ss, spec = st.session_state, _spec()
    with st.container(key="canvas", horizontal_alignment="center", vertical_alignment="center"):
        if df is None:
            st.markdown(
                '<div class="ec-empty"><b>Your chart appears here</b>'
                "<span>Load an MMA series or a file from the sidebar, "
                "or start from the sample.</span></div>",
                unsafe_allow_html=True,
                width="stretch",
            )
            st.button("Try sample data", type="primary", on_click=_load_sample, key="sample")
            return
        key = _preview_key(spec, df)
        cached = ss.preview_cache.get(key)
        if cached is None:
            t0 = time.perf_counter()
            try:
                res = render(spec, df)
                try:
                    png = figure_png_bytes(res.fig, PREVIEW_DPI)
                finally:
                    res.close()
                cached = {"png": png, "error": None, "secs": time.perf_counter() - t0}
            except Exception as exc:  # noqa: BLE001 — errors are shown, never crash the app
                cached = {"png": None, "error": str(exc) or exc.__class__.__name__, "secs": 0.0}
            ss.preview_cache = {key: cached}  # keep only the latest
        if cached["error"]:
            st.error(cached["error"])
            return
        st.image(cached["png"], width=PREVIEW_WIDTH)
        st.markdown(
            f'<div class="ec-stat">{cached["secs"]:.2f} s · 1080 × 1350 px export</div>',
            unsafe_allow_html=True,
        )


def export_buttons(df: Optional[pd.DataFrame], where: str) -> None:
    """Data .xlsx + Export PNG.  Drawn in the toolbar and (phones) under the inspector."""
    if df is None:
        st.button("Export PNG", type="primary", disabled=True, key=f"export.{where}.off")
        return
    frozen = ChartSpec.from_dict(_spec().to_dict())
    data = df.copy()
    st.download_button(
        "Data .xlsx",
        data=lambda: _export_xlsx(frozen, data),
        file_name="chart_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        on_click="ignore",
        key=f"export.{where}.xlsx",
    )
    st.download_button(
        "Export PNG",
        data=lambda: _export_png(frozen, data),
        file_name="chart.png",
        mime="image/png",
        type="primary",
        on_click="ignore",
        key=f"export.{where}.png",
    )


def _load_sample() -> None:
    """Open the bundled arrivals sample as a finished line chart."""
    ss = st.session_state
    for k in list(ss.keys()):
        if isinstance(k, str) and k.split(".")[0] in (
            "chart",
            "text",
            "step",
            "source",
            "axes",
            "layout",
            "colors",
            "style",
        ):
            del ss[k]
    ss.pop("chart_cols", None)
    ss.raw_df = pd.read_csv(SAMPLE_CSV)
    ss.raw_key = "sample"
    ss.source_label = "Sample · tourist arrivals by market"
    ss.load_error = None
    spec = ChartSpec()
    spec.source.kind = "file"
    spec.source.name = SAMPLE_CSV.name
    spec.steps = [StepSpec("pivot", {"index": "Year", "columns": "Market", "values": "Arrivals"})]
    spec.chart.type = "line"
    spec.chart.x_col = "Year"
    spec.chart.y_cols = ["China", "India", "Russia", "United Kingdom"]
    spec.style.text.title = "Tourist arrivals by\nsource market"
    spec.style.text.subtitle = "Arrivals per year, top four markets"
    spec.style.text.caption = "Source: Ministry of Tourism"
    ss.spec = spec
    ss.step_ids = [uuid.uuid4().hex[:8]]
    # Point the already-drawn segmented controls at the sample's choices.
    ss["chart.type"], ss["source.kind"] = spec.chart.type, spec.source.kind


def _preview_key(spec: ChartSpec, df: pd.DataFrame) -> str:
    spec_json = json.dumps(spec.to_dict(), sort_keys=True, default=str)
    df_hash = int(pd.util.hash_pandas_object(df, index=True).sum()) if len(df) else 0
    cols = "|".join(map(str, df.columns))
    return hashlib.sha1(f"{spec_json}|{df_hash}|{cols}".encode()).hexdigest()


def _export_png(spec: ChartSpec, df: pd.DataFrame) -> bytes:
    res = render(spec, df)
    try:
        return figure_png_bytes(res.fig, EXPORT_DPI)
    finally:
        res.close()


def _export_xlsx(spec: ChartSpec, df: pd.DataFrame) -> bytes:
    res = render(spec, df)
    try:
        return chart_data_xlsx_bytes(res.chart)
    finally:
        res.close()


# ── page ─────────────────────────────────────────────────────────────────────

_CSS = """
<style>
:root { --ec-stage: rgba(118, 118, 128, 0.08); --ec-rule: rgba(128, 128, 128, 0.18); }
.block-container { padding-top: 3rem; padding-bottom: 2rem; max-width: none; }
[data-testid="stAppDeployButton"] { display: none; }
.ec-logo { display: flex; align-items: center; gap: .5rem; font-weight: 700;
  font-size: 1.05rem; letter-spacing: -.01em; white-space: nowrap; }
.ec-logo i { width: 1.15rem; height: 1.15rem; border-radius: .35rem; flex: none;
  background: linear-gradient(160deg, #0077CC, #64D2FF); }
.ec-gh { font-size: .7rem; font-weight: 600; letter-spacing: .07em; text-transform: uppercase;
  opacity: .55; margin: .5rem 0 0; line-height: 1.4; }
.ec-file { display: flex; justify-content: space-between; gap: .5rem; font-size: .82rem;
  padding: .4rem .6rem; border-radius: 8px; background: var(--ec-stage); }
.ec-file span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.ec-file em { font-style: normal; opacity: .6; white-space: nowrap;
  font-variant-numeric: tabular-nums; }
.st-key-toolbar { border-bottom: 1px solid var(--ec-rule); padding-bottom: .65rem;
  margin-bottom: .5rem; }
.st-key-canvas { background: var(--ec-stage); border-radius: 16px; padding: 1.5rem 1rem 1rem;
  min-height: min(78vh, 720px); }
.st-key-canvas img { border-radius: 6px; box-shadow: 0 4px 18px rgba(0, 0, 0, .18); }
.ec-stat { text-align: center; font-size: .75rem; opacity: .6;
  font-variant-numeric: tabular-nums; }
.ec-strip { border: 1px dashed var(--ec-rule); border-radius: 9px; padding: .45rem .7rem .15rem;
  margin: .25rem 0 .5rem; }
.ec-strip > span { font-size: .68rem; letter-spacing: .07em; text-transform: uppercase;
  opacity: .6; }
.ec-axis { position: relative; height: 2.1rem; margin: .5rem 1.1rem 0;
  border-bottom: 2px solid currentColor; }
.ec-axis i { position: absolute; bottom: -6px; width: 1px; height: 6px;
  background: currentColor; }
.ec-axis em { position: absolute; top: 1.15rem; transform: translateX(-50%); font-style: normal;
  font-size: .68rem; white-space: nowrap; font-variant-numeric: tabular-nums; }
.ec-rail { display: grid; gap: .1rem; margin: 0 0 .75rem; padding: .5rem .65rem;
  border-radius: 10px; background: var(--ec-stage); }
.ec-step { display: grid; grid-template-columns: 1.4rem 1fr; gap: .55rem; padding: .25rem 0;
  align-items: start; }
.ec-step b { font-size: .82rem; font-weight: 600; display: block; }
.ec-step small { font-size: .72rem; opacity: .65; display: block; line-height: 1.3; }
.ec-step.next small { opacity: 1; }
.ec-step.optional b { font-weight: 500; }
.ec-badge { width: 1.25rem; height: 1.25rem; border-radius: 50%; display: grid; place-items: center;
  font-size: .68rem; font-weight: 700; background: rgba(128, 128, 128, .22); }
.ec-step.done .ec-badge { background: #1F8A4C; color: #fff; }
.ec-step.next .ec-badge { background: var(--primary-color, #0071E3); color: #fff; }
.ec-empty { display: grid; gap: .25rem; text-align: center; max-width: 30ch; margin: 0 auto; }
.ec-empty span { opacity: .65; font-size: .9rem; }
@media (min-width: 641px) {
  [data-testid="stColumn"]:has(.st-key-canvas) { position: sticky; top: 3.75rem;
    align-self: flex-start; }
  .st-key-mobile_export { display: none; }
}
@media (max-width: 640px) {
  .st-key-toolbar_export { display: none; }
  .st-key-canvas { min-height: auto; }
}
</style>
"""


def main() -> None:
    st.set_page_config(
        page_title="Chart Studio",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state=SIDEBAR_WIDTH,  # px; still auto-hides on phones
    )
    _state()
    st.markdown(_CSS, unsafe_allow_html=True)

    with st.container(key="toolbar"):
        brand, mid, actions = st.columns([1, 2, 1], vertical_alignment="center")
        brand.markdown('<div class="ec-logo"><i></i>Chart Studio</div>', unsafe_allow_html=True)
        with mid.container(horizontal_alignment="center"):
            chart_type_control()
        toolbar_export = actions.container(
            key="toolbar_export", horizontal=True, horizontal_alignment="right"
        )

    with st.sidebar:
        rail_slot = st.container()  # filled after the inspector, so it sees this run's choices
        df = data_panel()

    canvas, inspector = st.columns([2, 1], gap="medium")
    # The inspector updates the spec, so draw it before the canvas renders it.
    with inspector:
        inspector_panel(df)
        mobile_export = st.container(key="mobile_export", horizontal=True)
    with canvas:
        canvas_panel(df)
    with rail_slot:
        progress_rail(df)
    with toolbar_export:
        export_buttons(df, "toolbar")
    with mobile_export:
        export_buttons(df, "mobile")


main()
