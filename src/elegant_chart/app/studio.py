# elegant_chart/app/studio.py
"""
Chart Studio — Streamlit script.

Three panels: data + reshaping (left), live preview (centre), style tabs
(right).  Every widget reads from and writes to one ``ChartSpec`` kept in
``st.session_state``; the preview is drawn by :func:`elegant_chart.render`
— the real matplotlib renderer — so preview and download are the same image.

Run with ``elegant-chart-studio`` (or ``streamlit run`` on this file).
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import uuid
from typing import Any, Callable, Optional, Sequence

import matplotlib

matplotlib.use("Agg")

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from elegant_chart import sources  # noqa: E402
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


def data_panel() -> Optional[pd.DataFrame]:
    ss, spec = st.session_state, _spec()
    st.subheader("Data")
    kind = st.radio(
        "Source",
        ["mma", "file"],
        horizontal=True,
        key="source.kind",
        index=0 if spec.source.kind != "file" else 1,
        format_func=lambda k: "MMA series" if k == "mma" else "Excel / CSV file",
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
                ss.load_error = None
            except Exception as exc:  # noqa: BLE001 — shown to the user, never crashes the app
                ss.load_error = str(exc)
        st.caption("Uses MMA_API_TOKEN / TOKEN.txt and the local Excel cache.")
    else:
        up = st.file_uploader(
            "Upload .xlsx or .csv", type=["xlsx", "xlsm", "csv"], key="source.upload"
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
                spec.source.name, spec.source.sheet = up.name, sheet
            except Exception as exc:  # noqa: BLE001
                ss.load_error = str(exc)

    if ss.load_error:
        st.error(ss.load_error)
    raw = ss.raw_df
    if raw is None:
        st.info("Load data to start.")
        return None
    st.caption(f"{len(raw):,} rows × {len(raw.columns)} columns loaded")

    st.subheader("Reshape")
    current = raw
    failed = False
    for i, step in enumerate(list(spec.steps)):
        sid = ss.step_ids[i]
        title = f"{i + 1}. {STEP_LABELS.get(step.op, step.op)}"
        if failed:
            with st.expander(f"{title} — skipped", expanded=False):
                st.caption("Skipped: an earlier step failed.")
                _step_controls(i, step, sid, list(current.columns))
            continue
        with st.expander(title, expanded=True):
            _step_controls(i, step, sid, list(current.columns))
            try:
                current = apply_step(current, step.op, step.params)
                st.caption(f"→ {len(current):,} rows")
            except Exception as exc:  # noqa: BLE001
                failed = True
                st.error(str(exc) or exc.__class__.__name__)

    c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
    new_op = c1.selectbox("Add step", STEP_OPS, format_func=STEP_LABELS.get, key="new_step_op")
    c2.button("＋ Add", on_click=_add_step, args=(new_op,), width="stretch")

    result = run_pipeline(raw, spec.steps)  # the library pipeline is the source of truth
    st.dataframe(result.df.head(200), height=240, width="stretch")
    if len(result.df) > 200:
        st.caption(f"Showing 200 of {len(result.df):,} rows")
    return result.df


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
        p["ascending"] = st.checkbox("Ascending", value=bool(p.get("ascending")), key=f"{k}.asc")
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


def style_panel(df: Optional[pd.DataFrame]) -> None:
    spec = _spec()
    st.subheader("Style")
    tabs = st.tabs(["Chart", "Text", "Layout", "Axes", "Colors", "Legend"])
    with tabs[0]:
        chart_tab(spec, df)
    with tabs[1]:
        text_tab(spec)
    with tabs[2]:
        layout_tab(spec)
    with tabs[3]:
        axes_tab(spec)
    with tabs[4]:
        colors_tab(spec, df)
    with tabs[5]:
        st.caption("A legend is drawn only when two or more series are plotted.")
        spec.style.legend.legend_ncol = _opt_number(
            "Legend columns",
            spec.style.legend.legend_ncol,
            "style.legend.ncol",
            integer=True,
            min_value=1,
            help="Empty = min(3, number of series)",
        )


def chart_tab(spec: ChartSpec, df: Optional[pd.DataFrame]) -> None:
    ch = spec.chart
    ch.type = st.radio(
        "Chart type",
        CHART_TYPES,
        index=CHART_TYPES.index(ch.type),
        format_func=CHART_TYPE_LABELS.get,
        horizontal=True,
        key="chart.type",
    )
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
        ch.x_col = _select("X column (categories / periods)", cols, ch.x_col, "chart.x_col")
        numeric = [c for c in df.select_dtypes("number").columns if c != ch.x_col]
        ch.y_cols = st.multiselect(
            "Series column(s)",
            numeric,
            default=[c for c in ch.y_cols if c in numeric] or numeric,
            key="chart.y_cols",
        )
    else:
        st.caption("Load data to choose columns.")

    if ch.type in ("bar", "hbar", "line"):
        ch.show_value_labels = st.checkbox(
            "Value labels", ch.show_value_labels, key="chart.show_value_labels"
        )
    if ch.type in ("bar", "line"):
        c1, c2 = st.columns(2)
        ch.rotation = c1.number_input(
            "X label rotation",
            value=float(ch.rotation),
            step=15.0,
            key="chart.rotation",
            format="%g",
        )
        ch.compact_years = c2.checkbox(
            "Compact years ('21)", ch.compact_years, key="chart.compact_years"
        )
    if ch.type == "bar":
        ch.stacked = st.checkbox("Stacked", ch.stacked, key="chart.stacked")
    if ch.type in ("bar", "hbar"):
        ch.bar_width = _opt_number(
            "Bar width", ch.bar_width, "chart.bar_width", step=0.05, min_value=0.0
        )
    if ch.type == "line":
        ch.markers = st.checkbox("Markers", ch.markers, key="chart.markers")
        ch.linewidth = _opt_number(
            "Line width (pt)", ch.linewidth, "chart.linewidth", step=0.1, min_value=0.0
        )
    if ch.type == "bump":
        series = list(ch.y_cols) if ch.y_cols else []
        ch.highlight = st.multiselect(
            "Highlight (empty = all)",
            series,
            default=[s for s in ch.highlight if s in series],
            key="chart.highlight",
        )
        ch.ascending = st.checkbox("Smallest value = rank 1", ch.ascending, key="chart.ascending")
        bump_style_controls(ch, series)
    if ch.type in ("hbar", "bump"):
        logos_editor(spec, df)


def bump_style_controls(ch: Any, series: list) -> None:
    """Ghost-line colour/opacity, line widths and label text for bump charts."""
    st.markdown("**Lines**")
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
    st.markdown("**Label text**")
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


def logos_editor(spec: ChartSpec, df: Optional[pd.DataFrame]) -> None:
    ch = spec.chart
    if df is None or df.empty or ch.x_col not in df.columns:
        return
    labels = (
        [str(v) for v in df[ch.x_col].tolist()]
        if ch.type == "hbar"
        else [str(c) for c in ch.y_cols]
    )
    st.markdown("**Label logos**")
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
    st.markdown("**Annotations**")
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
    lay.align_x_edges = st.checkbox(
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
    lay.show_footer = st.checkbox(
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
    lay.y_tick_labels_inside = st.checkbox(
        "Y tick labels inside the plot", lay.y_tick_labels_inside, key="layout.y_inside"
    )
    lay.show_y_axis = st.checkbox(
        "Show y gridlines + labels", lay.show_y_axis, key="layout.show_y_axis"
    )
    lay.show_y_spine = st.checkbox("Show y spine", lay.show_y_spine, key="layout.show_y_spine")


def axes_tab(spec: ChartSpec) -> None:
    a, ctype = spec.style.axes, spec.chart.type
    if ctype == "bump":
        st.caption("Bump charts place their own rank axis; these settings don't apply.")
    c1, c2 = st.columns(2)
    with c1:
        a.x_tick_step = _opt_number("X tick step", a.x_tick_step, "axes.x_tick_step")
        a.y_tick_step = _opt_number("Y tick step", a.y_tick_step, "axes.y_tick_step")
        a.x_minor_ticks = _opt_number(
            "X minor ticks per interval",
            a.x_minor_ticks,
            "axes.x_minor_ticks",
            integer=True,
            min_value=0,
        )
    with c2:
        a.max_x_ticks = _opt_number(
            "Max x ticks", a.max_x_ticks, "axes.max_x_ticks", integer=True, min_value=1
        )
        a.max_y_ticks = _opt_number(
            "Max y ticks", a.max_y_ticks, "axes.max_y_ticks", integer=True, min_value=1
        )
        a.x_year_tick_interval = _opt_number(
            "Year tick interval (line)",
            a.x_year_tick_interval,
            "axes.x_year_tick_interval",
            integer=True,
            min_value=1,
        )
    a.auto_x_thinning = st.checkbox(
        "Auto-thin crowded x labels", a.auto_x_thinning, key="axes.auto_x_thinning"
    )
    a.x_date_format = (
        st.text_input(
            "X date format (e.g. %Y, %b %y)", a.x_date_format or "", key="axes.x_date_format"
        )
        or None
    )
    a.xlim = _range("X", a.xlim, "axes.xlim")
    a.ylim = _range("Y", a.ylim, "axes.ylim")
    a.y_formatter = _select(
        "Value format",
        Y_FORMATTERS,
        a.y_formatter,
        "axes.y_formatter",
        fmt={
            "compact": "Compact (1.2K)",
            "plain": "Plain",
            "percent": "Percent (0.1 → 10%)",
            "norm_max": "Normalised to max",
            "custom": "Custom",
        }.get,
    )
    if a.y_formatter == "norm_max":
        a.y_formatter_decimals = int(
            st.number_input("Decimals", 0, 6, int(a.y_formatter_decimals), key="axes.y_decimals")
        )
    if a.y_formatter == "custom":
        a.y_formatter_custom = st.text_input(
            "Format string",
            a.y_formatter_custom,
            key="axes.y_custom",
            help="Python format, e.g. {x:,.1f}",
        )


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
    for i, lbl in enumerate(labels):
        cur = c.color_map.get(lbl)
        choice = "auto" if cur is None else (cur if cur in COLOR_ROLES else "custom")
        c1, c2, c3 = st.columns([2, 1, 2], vertical_alignment="bottom")
        with c1:
            choice = _select(lbl, options, choice, f"colors.role.{lbl}")
        if choice == "custom":
            new_map[lbl] = c2.color_picker(
                "Hex", cur if cur and cur.startswith("#") else "#64D2FF", key=f"colors.hex.{lbl}"
            )
        elif choice != "auto":
            new_map[lbl] = choice
        if spec.chart.type != "bump":
            alpha = c3.slider(
                "Opacity",
                0.0,
                1.0,
                float(c.alpha_map.get(lbl, 1.0)),
                0.05,
                key=f"colors.alpha.{lbl}",
            )
            if alpha < 1.0:
                new_alpha[lbl] = alpha
    c.color_map, c.alpha_map = new_map, new_alpha


# ── centre panel: preview + downloads ────────────────────────────────────────


def preview_panel(df: Optional[pd.DataFrame]) -> None:
    ss, spec = st.session_state, _spec()
    st.subheader("Preview")
    if df is None:
        st.info("The live preview appears here once data is loaded.")
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
    st.image(cached["png"], width=480)
    st.caption(
        f"Rendered in {cached['secs']:.2f} s · preview {PREVIEW_DPI} dpi, "
        f"export {EXPORT_DPI} dpi (1080 × 1350 px)"
    )

    frozen = ChartSpec.from_dict(spec.to_dict())
    data = df.copy()
    c1, c2 = st.columns(2)
    c1.download_button(
        "Download PNG",
        data=lambda: _export_png(frozen, data),
        file_name="chart.png",
        mime="image/png",
        type="primary",
        on_click="ignore",
        width="stretch",
    )
    c2.download_button(
        "Download chart_data.xlsx",
        data=lambda: _export_xlsx(frozen, data),
        file_name="chart_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        on_click="ignore",
        width="stretch",
    )


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


def main() -> None:
    st.set_page_config(page_title="Chart Studio", layout="wide")
    _state()
    st.markdown(
        "<style>.block-container{padding-top:1.5rem;padding-bottom:1rem}</style>",
        unsafe_allow_html=True,
    )
    left, centre, right = st.columns([1.15, 1.25, 1.2], gap="medium")
    with left:
        df = data_panel()
    # Style widgets update the spec, so draw them before the preview renders it.
    with right:
        style_panel(df)
    with centre:
        preview_panel(df)


main()
