# examples/line_maldives_reserves_history.py
"""
Maldives total reserves, months of import cover - full annual history,
1979-2024, with the IMF's 3-month adequacy threshold (and a shaded
below-threshold danger zone) plus callouts on the pre-2020 high, the
COVID-era peak, and the latest value.

Companion long-run view to line_maldives_fx_reserves.py, which zooms into
the recent Sep 2024-Apr 2026 drawdown this series ends just before.

X is numeric (plain int years), not categorical, since the series is an
unbroken yearly run - matches the GDP-growth pattern in line_minimal.py.
"""

from elegant_chart import ElegantChart

years = list(range(1979, 2025))
values = [
    0.177020213,
    0.126834994,
    0.141555404,
    1.014856944,
    0.511196644,
    0.571035484,
    0.559427618,
    0.781766481,
    0.879558472,
    2.032519365,
    1.899099507,
    1.646073154,
    1.390250299,
    1.42572716,
    1.221117536,
    1.329013048,
    1.707678434,
    2.39709541,
    2.704962794,
    3.181241993,
    3.038139159,
    2.995228292,
    2.227123937,
    3.215339282,
    3.30454721,
    3.184632999,
    2.456420359,
    2.519521241,
    1.904716557,
    1.212619541,
    1.781203218,
    2.091739329,
    1.548090738,
    1.508228657,
    1.597042532,
    2.368067254,
    2.174587254,
    1.573415511,
    1.812375379,
    1.852367717,
    1.940234875,
    4.26800655,
    2.399264192,
    1.75611906,
    1.22268411,
    1.303262559,
]

IMF_THRESHOLD = 3.0
DANGER_RED = "#C0392B"

chart = ElegantChart(
    title="Maldives Reserves:\nFour Decades of Volatility",
    subtitle="Months of import cover, 1979–2024",
    caption="Source: World Bank\nData Visualized by Hassan Shammu\n",
    theme="newsroom_dark",
    ylim=(0, 4.6),
    y_tick_step=1,
    y_formatter="plain",
    annotations=[
        {
            # Reference-line label, lifted clear of the dashed line.
            "x": years[0],
            "y": IMF_THRESHOLD,
            "text": "IMF adequacy threshold (3 months)",
            "dx": 0,
            "dy": 9,
            "ha": "left",
            "va": "bottom",
            "arrow": True,
        },
        {
            "x": 2003,
            "y": values[2003 - 1979],
            "text": "Pre-2020 high —\n3.3 months (2003)",
            "dx": -4,
            "dy": 14,
            "ha": "right",
            "va": "bottom",
            "arrow": True,
        },
        {
            # Pulled left of the spike (ha="right") so the text grows away
            # from the right edge instead of bleeding past it.
            "x": 2020,
            "y": values[2020 - 1979],
            "text": "COVID-era peak —\n4.3 months (2020)",
            "dx": -4,
            "dy": 16,
            "ha": "right",
            "va": "bottom",
            "arrow": True,
        },
        {
            # Dropped into the open floor below the last point, instead of
            # above where it would cross the steep 2020-2024 drawdown line.
            "x": 2024,
            "y": values[2024 - 1979],
            "text": "Latest —\n1.3 months (2024)",
            "dx": -10,
            "dy": -12,
            "ha": "right",
            "va": "top",
            "arrow": True,
        },
    ],
)

fig, ax = chart.line(
    x=years,
    ys=[values],
    labels=["Months of import cover"],
    markers=False,
    linewidth=1.0,
    y_formatter="plain",
    save_path=None,
    show=False,
)

# Below-threshold danger zone, drawn behind the gridlines/line/markers.
ax.axhspan(0, IMF_THRESHOLD, color=DANGER_RED, alpha=0.08, zorder=-1, lw=0)
ax.axhline(
    IMF_THRESHOLD,
    color=chart.color_annotation,
    linestyle="--",
    linewidth=chart._px(0.5),
    zorder=1,
)

chart.save_figure(fig, "line_maldives_reserves_history.png", dpi=500)
chart.export_data("chart_data.xlsx")
