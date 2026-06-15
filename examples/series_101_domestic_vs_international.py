# examples/series_101_domestic_vs_international.py
"""
Domestic vs international passenger traffic (Maldives), 2021-2023 -
grouped bar chart built from data/series_101.xlsx.
"""

import pandas as pd

from elegant_chart import ElegantChart

df = pd.read_excel("data/series_101.xlsx")

pivot = df.pivot_table(
    index="Year", columns="Type", values="Total Passengers", aggfunc="sum"
).sort_index()

chart = ElegantChart(
    title="International Travel Drives\nthe Post-Pandemic Recovery",
    subtitle="Total passengers by travel type, millions",
    caption="Source: Maldives Bureau of Statistics\nData Visualized by Hassan Shammu\n",
    theme="newsroom_dark",
    color_map={"Domestic": "secondary", "International": "primary"},
    show_y_axis=False,
)

chart.bar(
    x=pivot.index.tolist(),
    ys=[pivot["Domestic"].tolist(), pivot["International"].tolist()],
    labels=["Domestic", "International"],
    show_value_labels=True,
    y_formatter="compact",
    x_tick_step=1,
    stacked=True,
    show=False,
    save_path="series_101_domestic_vs_international.png",
)
