# examples/series_101_top10_airlines.py
"""
Top 10 airlines by total passengers, 2021-2023 combined - bar chart built
from data/series_101.xlsx.
"""

import pandas as pd

from elegant_chart import ElegantChart

df = pd.read_excel("data/series_101.xlsx")

top10 = (
    df[df["Type"] == "International"]
    .groupby("Airline")["Total Passengers"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

chart = ElegantChart(
    title="Top 10 Airlines\nby Passengers Carried",
    subtitle="International passengers, 2020-2023 combined",
    caption="Source: Maldives Bureau of Statistics\nData Visualized by Hassan Shammu\n",
    theme="newsroom_dark",
    color_map={"Total Passengers": "#64D2FF"},
)

chart.bar(
    x=top10.index.tolist(),
    ys=top10.tolist(),
    labels=["Total Passengers"],
    horizontal=True,
    show_value_labels=True,
    y_formatter="compact",
    max_label_width=20,
    label_width_strategy="truncate",
    show=False,
    save_path="series_101_top10_airlines.png",
)
