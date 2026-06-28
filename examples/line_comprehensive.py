# examples/line_comprehensive.py
"""
Comprehensive line() example — every constructor option and every line()
argument is set explicitly, with a short comment explaining each one.

Self-contained: copy this whole file and run it as-is. It uses a datetime
x-axis with two series so that the datetime-axis knobs (x_minor_ticks,
x_upper_pad, align_x_edges) all have a visible effect.

Note: `df`/`x_col`/`y_cols` are an alternative input mode to `x`/`ys`/`labels`
— they are mutually exclusive, so they are left as None here. `x_tick_step`
and `x_formatter` only apply to numeric (non-datetime) x-axes; they are
still listed below for completeness, set to values that are no-ops here.
"""

import pandas as pd

from elegant_chart import ElegantChart

# ── Mock data: two monthly series over 2 years ────────────────────────────
dates = pd.date_range("2022-01", periods=24, freq="MS")
resorts = [
    62,
    64,
    68,
    71,
    70,
    73,
    75,
    78,
    80,
    79,
    81,
    83,
    85,
    86,
    88,
    90,
    89,
    91,
    92,
    94,
    95,
    96,
    97,
    98,
]
guesthouses = [
    40,
    41,
    43,
    45,
    46,
    48,
    50,
    52,
    53,
    54,
    55,
    57,
    58,
    59,
    61,
    62,
    63,
    65,
    66,
    67,
    68,
    69,
    70,
    71,
]

# ── Constructor: every ChartBase / mixin attribute set explicitly ─────────
chart = ElegantChart(
    title="Maldives Occupancy Rates",  # main heading, top-left
    subtitle="Occupancy %, by accommodation type",  # smaller line under the title
    xlabel="Month",  # x-axis label (bottom)
    ylabel="Occupancy %",  # y-axis label (right, by default)
    caption="Source: Mock data for demonstration",  # footer text, bottom-left
    figsize=(2.16, 2.70),  # inches; default = 1080x1350 px @ 500 DPI
    theme="newsroom_dark",  # consulting_light | consulting_dark | newsroom_muted | newsroom_dark
    color_map={
        "Resorts": "primary",
        "Guesthouses": "secondary",
    },  # series label -> role name or hex
    font_scale=0.9,  # multiplier applied to all font sizes
    dpi=150,  # on-screen render DPI (save_dpi controls file output)
    x_tick_step=None,  # numeric-axis only; no effect on datetime x
    max_x_ticks=6,  # cap on interior datetime/numeric ticks
    auto_x_thinning=True,  # auto-thin categorical labels to avoid overlap
    y_tick_step=None,  # let the locator pick y tick spacing
    max_y_ticks=5,  # cap on the number of y ticks
    y_formatter="plain",  # "compact" | "plain" | "percent" | ("norm_max", n) | callable
    xlim=None,  # let the data define the x range
    ylim=(0, 100),  # fix the y-axis range
    x_minor_ticks=1,  # 1 unlabeled minor tick between each pair of major ticks
    x_upper_pad=0.05,  # extra right-side x padding, as a fraction of the data span
    align_x_edges=True,  # keep first/last tick labels centered, padded so they don't clip
    logo_path=None,  # path to a footer logo image; None disables it
    logo_height_rel=0.12,  # logo height as a fraction of figure height
    logo_margin_rel=0.02,  # logo right margin as a fraction of figure width
    show_footer=True,  # draw the caption/logo footer band at all
    y_axis_side="right",  # "right" | "left" — side the y-axis labels live on
    y_tick_labels_inside=True,  # draw y tick labels inside the plot area
    show_y_spine=False,  # draw the y-axis spine line
    annotations=None,  # optional list of in-plot callout dicts
)

# ── line(): every argument set explicitly ──────────────────────────────────
fig, ax = chart.line(
    x=dates,  # x values: categorical, numeric, or datetime
    ys=[resorts, guesthouses],  # list of series (or dict / single sequence)
    labels=["Resorts", "Guesthouses"],  # legend labels, one per series in `ys`
    df=None,  # alternative: pass a DataFrame instead of x/ys/labels
    x_col=None,  # column name for x, used with df
    y_cols=None,  # column name(s) for y, used with df
    rotation=0,  # x tick label rotation, in degrees
    markers=True,  # draw a marker at each data point
    linewidth=1.2,  # line width in points; None = auto-scaled default
    show_value_labels=False,  # print each point's value above it
    compact_years=False,  # abbreviate year-like string labels (no effect on datetime x)
    x_tick_step=None,  # numeric-axis only; no effect here
    max_x_ticks=6,
    auto_x_thinning=True,
    max_label_width=None,  # wrap/truncate x labels longer than this many characters
    label_width_strategy="wrap",  # "wrap" | "truncate"
    tick_label_pad=None,  # extra padding between ticks and their labels
    y_tick_step=None,
    max_y_ticks=5,
    y_formatter="plain",
    x_formatter=None,  # numeric-axis only; no effect on datetime x
    xlim=None,
    ylim=(0, 100),
    x_minor_ticks=1,
    x_upper_pad=0.05,
    align_x_edges=True,
    show=True,  # open an interactive window
    save_path="line_comprehensive.png",  # write the chart image here
    save_dpi=500,  # DPI used for the saved image
    save_format=None,  # inferred from save_path's extension when None
    export_xlsx=True,  # also write the underlying data to .xlsx next to save_path
    export_xlsx_path=None,  # custom path for the exported .xlsx; defaults to chart_data.xlsx
)
