# examples/aircraft_movement_domestic.py
"""
Monthly seasonality of domestic aircraft movements - line chart built from
data/series_102.xlsx, averaged across all airports and all years.
"""

import pandas as pd

from elegant_chart import ElegantChart

MONTH_ORDER = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

df = pd.read_excel("data/series_102.xlsx", sheet_name="Aircraft Movements Data", skiprows=3)
df = df[df["Year"] >= 2018]

monthly_avg = (
    df[df["Month"] != "Total"].groupby("Month")["Aircraft Movements"].mean().reindex(MONTH_ORDER)
)

# January spelled out to anchor the year start; the rest as a single letter.
month_labels = ["Jan"] + [m[0] for m in MONTH_ORDER[1:]]

chart = ElegantChart(
    title="Domestic Flights Peak in\nJanuary; Drop Every June",
    subtitle="Monthly average aircraft movements,\nall Maldives domestic airports, 2018–24",
    caption="Source: Maldives Bureau of Statistics\nData Visualized by Hassan Shammu\n",
    theme="newsroom_dark",
    color_map={"Average movements": "#64D2FF"},
)

chart.line(
    x=month_labels,
    ys=monthly_avg.tolist(),
    labels=["Average movements"],
    linewidth=1.5,
    y_formatter="compact",
    max_x_ticks=12,
    auto_x_thinning=False,
    markers=False,
    show=False,
    save_path="aircraft_movement_domestic.png",
)
