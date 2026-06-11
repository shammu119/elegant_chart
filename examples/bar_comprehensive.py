# examples/bar_comprehensive.py
"""
Comprehensive bar() example — every constructor option and every bar()
argument is set explicitly, with a short comment explaining each one.

Self-contained: copy this whole file and run it as-is. It uses a numeric
(year) x-axis with two grouped series so that the numeric-axis-only knobs
(x_tick_step, x_formatter, x_minor_ticks, x_upper_pad) all have a visible
effect.

Note: `df`/`x_col`/`y_cols` are an alternative input mode to `x`/`ys`/`labels`
(see bar_minimal.py for the DataFrame form) — they are mutually exclusive,
so they are left as None here.
"""

from elegant_chart import ElegantChart

# ── Mock data: two series across 10 years ─────────────────────────────────
years = list(range(2014, 2024))
exports = [120, 135, 128, 142, 150, 138, 95, 160, 175, 182]
imports = [180, 190, 185, 200, 210, 205, 150, 220, 235, 240]

# ── Constructor: every ChartBase / mixin attribute set explicitly ─────────
chart = ElegantChart(
    title="Maldives Trade Balance",  # main heading, top-left
    subtitle="Exports vs imports, USD millions",  # smaller line under the title
    xlabel="Year",  # x-axis label (bottom)
    ylabel="USD M",  # y-axis label (right, by default)
    caption="Source: Mock data for demonstration",  # footer text, bottom-left
    figsize=(2.16, 2.70),  # inches; default = 1080x1350 px @ 500 DPI
    theme="consulting_light",  # consulting_light | consulting_dark | newsroom_muted | newsroom_dark
    color_map={"Exports": "secondary", "Imports": "primary"},  # series label -> role name or hex
    font_scale=0.9,  # multiplier applied to all font sizes
    dpi=150,  # on-screen render DPI (save_dpi controls file output)
    x_tick_step=2,  # major x tick every 2 years
    max_x_ticks=None,  # cap on interior ticks; ignored when x_tick_step is set
    auto_x_thinning=True,  # auto-thin categorical labels to avoid overlap
    y_tick_step=50,  # major y tick every 50 units
    max_y_ticks=None,  # cap on y ticks; ignored when y_tick_step is set
    y_formatter="plain",  # "compact" | "plain" | "percent" | ("norm_max", n) | callable
    xlim=None,  # let the data define the x range
    ylim=(0, 260),  # fix the y-axis range
    x_minor_ticks=1,  # 1 unlabeled minor tick between each pair of major ticks
    x_upper_pad=0.05,  # extra right-side x padding, as a fraction of the data span
    align_x_edges=True,  # left-align first / right-align last x tick label
    logo_path=None,  # path to a footer logo image; None disables it
    logo_height_rel=0.12,  # logo height as a fraction of figure height
    logo_margin_rel=0.02,  # logo right margin as a fraction of figure width
    show_footer=True,  # draw the caption/logo footer band at all
    y_axis_side="right",  # "right" | "left" — side the y-axis labels live on
    y_tick_labels_inside=True,  # draw y tick labels inside the plot area
    show_y_spine=False,  # draw the y-axis spine line
    annotations=None,  # optional list of in-plot callout dicts
)

# ── bar(): every argument set explicitly ───────────────────────────────────
fig, ax = chart.bar(
    x=years,  # x values: categorical, numeric, or datetime
    ys=[exports, imports],  # list of series (or dict / single sequence)
    labels=["Exports", "Imports"],  # legend labels, one per series in `ys`
    df=None,  # alternative: pass a DataFrame instead of x/ys/labels
    x_col=None,  # column name for x, used with df
    y_cols=None,  # column name(s) for y, used with df
    rotation=0,  # x tick label rotation, in degrees
    stacked=False,  # stack series instead of grouping them side by side
    bar_width=0.8,  # total width of a bar group, in x-axis units
    show_value_labels=False,  # print each bar's value above it
    compact_years=False,  # abbreviate year-like string labels (no effect on numeric x here)
    x_tick_step=2,  # overrides the constructor default for this call
    max_x_ticks=None,
    auto_x_thinning=True,
    max_label_width=None,  # wrap/truncate x labels longer than this many characters
    label_width_strategy="wrap",  # "wrap" | "truncate"
    tick_label_pad=None,  # extra padding between ticks and their labels
    y_tick_step=50,
    max_y_ticks=None,
    y_formatter="plain",
    x_formatter="plain",  # formatter for numeric x tick labels
    xlim=None,
    ylim=(0, 260),
    x_minor_ticks=1,
    x_upper_pad=0.05,
    align_x_edges=True,
    show=True,  # open an interactive window
    save_path="bar_comprehensive.png",  # write the chart image here
    save_dpi=500,  # DPI used for the saved image
    save_format=None,  # inferred from save_path's extension when None
    export_xlsx=True,  # also write the underlying data to .xlsx next to save_path
    export_xlsx_path=None,  # custom path for the exported .xlsx; defaults to chart_data.xlsx
)
