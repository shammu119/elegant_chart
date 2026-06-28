# examples/line_maldives_fx_reserves.py
"""
Maldives FX reserves, months of import cover - line chart with a fixed
IMF adequacy threshold, a shaded below-threshold danger zone, a policy-event
marker, and annotated callouts on the historic low, the peak, and the
post-peak drawdown.

Illustrative data for demonstration purposes (not an official MMA/IMF series).

X is treated as 7 categorical labels, not a time scale, so the (real-world)
uneven gaps between dates don't distort spacing. Nov 2024 - Mar 2025 are
flagged as estimated interpolation points: line() only draws one uniform
style per series, so the line/markers are built manually in two passes
(dashed+light for the estimated stretch, solid for the confirmed stretch)
on top of an invisible line() call that still does all the axis/grid/footer
scaffolding.
"""

from elegant_chart import ElegantChart

labels = ["Sep24", "Nov24", "Jan25", "Mar25", "Jul25", "Mar26", "Apr26"]
values = [0.8, 1.1, 1.3, 1.5, 1.8, 2.6, 1.4]
positions = list(range(len(labels)))

REAL_IDX = [0, 5, 6]  # Sep 2024, Mar 2026, Apr 2026 - confirmed data points
ESTIMATED_IDX = [1, 2, 3]  # Nov 2024, Jan 2025, Mar 2025 - interpolated for continuity
POLICY_IDX = 4  # Jul 2025 - MMA policy event

IMF_THRESHOLD = 3.0
DANGER_RED = "#C0392B"

chart = ElegantChart(
    title="Maldives FX Reserves\nNear Depletion",
    subtitle="Months of import cover, Sep 2024–Apr 2026",
    # ylabel is intentionally omitted: at this canvas's right=0.97 margin, a
    # right-side ylabel renders almost entirely clipped (see library quirk
    # with y_axis_side="right" + y_tick_labels_inside). The subtitle above
    # already states the unit, matching this codebase's documented fallback
    # of letting the subtitle name the metric instead of an axis label.
    caption="Source: MMA\nData Visualized by Hassan Shammu\n",
    theme="newsroom_dark",
    ylim=(0, 3.5),
    y_tick_step=0.5,
    y_formatter="plain",
    annotations=[
        # Reference-line label, lifted clear of the dashed line with a short
        # leader line back down to it.
        {
            "x": positions[0],
            "y": IMF_THRESHOLD,
            "text": "IMF adequacy threshold (3 months)",
            "dx": 0,
            "dy": 9,
            "ha": "left",
            "va": "bottom",
            "arrow": True,
        },
        {
            # Dropped into the open floor below the historic low, instead of
            # crowding the marker directly (kept short of y=0 so it doesn't
            # run into the x-tick labels below the axis).
            "x": positions[0],
            "y": values[0],
            "text": "Historic low —\n0.8 months / $371M",
            "dx": 4,
            "dy": -10,
            "ha": "left",
            "va": "top",
            "arrow": True,
        },
        {
            # Pulled down into the open wedge under the peak and right of
            # the policy diamond, clear of both the threshold ceiling above
            # and the diamond's own footprint.
            "x": positions[5],
            "y": values[5],
            "text": "Bilateral support —\n2.6 months / $1.3B",
            "dx": 6,
            "dy": -20,
            "ha": "center",
            "va": "top",
            "arrow": True,
        },
        {
            # Dropped further into the open floor on the right, clear of
            # Bilateral support's band above it.
            "x": positions[6],
            "y": values[6],
            "text": "Sukuk repayment —\n1.4 months / $718M",
            "dx": -2,
            "dy": -24,
            "ha": "right",
            "va": "top",
            "arrow": True,
        },
        {
            # Lifted up and pulled left over the dashed (estimated) segment,
            # clear of Bilateral support's and Sukuk repayment's bands.
            "x": positions[POLICY_IDX],
            "y": values[POLICY_IDX],
            "text": "MMA cuts reserve\nrequirement to 5%",
            "dx": -10,
            "dy": 18,
            "ha": "right",
            "va": "bottom",
            "arrow": True,
        },
    ],
)

# Render with the auto-line/markers suppressed (linewidth=0, markers=False):
# this call still builds the grid, axis ticks, boundary spine, and footer,
# while keeping the real 7-point series cached for export_data().
fig, ax = chart.line(
    x=labels,
    ys=[values],
    labels=["Months of import cover"],
    markers=False,
    linewidth=0,
    align_x_edges=False,  # keep edge labels centered; xlim padding below clears them instead
    save_path=None,
    show=False,
)

# Expand the x-limits by half the rendered width of the first/last tick
# label so the now-centered edge labels ("Sep24", "Apr26") have room to sit
# under their ticks without bleeding off the canvas. This is the same
# pixel-to-data-span technique FigureMixin._apply_year_comb_left_padding
# uses for the datetime year-comb axis, applied here to both edges since
# this is a categorical axis (that helper only fires for the year comb).
fig.canvas.draw()
_renderer = fig.canvas.get_renderer()
_ax_bbox = ax.get_window_extent(_renderer)
_xticklabels = ax.get_xticklabels()
_lo, _hi = ax.get_xlim()
_span = _hi - _lo
_first_w = _xticklabels[0].get_window_extent(_renderer).width
_last_w = _xticklabels[-1].get_window_extent(_renderer).width
_p_lo = (_first_w / 2) / _ax_bbox.width
_p_hi = (_last_w / 2) / _ax_bbox.width
_pad_lo = (_p_lo / (1 - _p_lo)) * _span
_pad_hi = (_p_hi / (1 - _p_hi)) * _span
ax.set_xlim(_lo - _pad_lo, _hi + _pad_hi)

primary = chart.color_roles["primary"]
policy_color = chart.color_roles["tertiary"]

# Below-threshold danger zone, drawn behind the gridlines/line/markers.
ax.axhspan(0, IMF_THRESHOLD, color=DANGER_RED, alpha=0.08, zorder=-1, lw=0)
ax.axhline(
    IMF_THRESHOLD,
    color=chart.color_annotation,
    linestyle="--",
    linewidth=chart._px(0.5),
    zorder=1,
)

# Estimated stretch (Sep 2024 -> Jul 2025): dashed and lighter to flag the
# Nov 2024 / Jan 2025 / Mar 2025 points as interpolated, not measured.
ax.plot(
    positions[: POLICY_IDX + 1],
    values[: POLICY_IDX + 1],
    color=primary,
    alpha=0.45,
    linewidth=chart._px(0.9),
    linestyle="--",
    zorder=2,
)
# Confirmed stretch (Jul 2025 -> Apr 2026): solid, full opacity.
ax.plot(
    positions[POLICY_IDX:],
    values[POLICY_IDX:],
    color=primary,
    linewidth=chart._px(0.9),
    zorder=2,
)

# Real points: solid filled circles.
ax.scatter(
    [positions[i] for i in REAL_IDX],
    [values[i] for i in REAL_IDX],
    s=chart._px(3.0) ** 2,
    color=primary,
    zorder=3,
)
# Estimated points: hollow circles to read as lighter/provisional.
ax.scatter(
    [positions[i] for i in ESTIMATED_IDX],
    [values[i] for i in ESTIMATED_IDX],
    s=chart._px(2.4) ** 2,
    facecolors=chart.bg_color,
    edgecolors=primary,
    alpha=0.7,
    linewidth=chart._px(0.6),
    zorder=3,
)
# Policy marker: distinct shape and color.
ax.scatter(
    positions[POLICY_IDX],
    values[POLICY_IDX],
    s=chart._px(4.2) ** 2,
    marker="D",
    color=policy_color,
    zorder=4,
)

chart.save_figure(fig, "line_maldives_fx_reserves.png", dpi=500)
chart.export_data("chart_data.xlsx")
