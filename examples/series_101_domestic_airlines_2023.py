# examples/series_101_domestic_airlines_2023.py
"""
Domestic airlines by total passengers, 2023 - bar chart built from
data/series_101.xlsx.
"""

import pandas as pd

from elegant_chart import ElegantChart

df = pd.read_excel("data/series_101.xlsx")

domestic_2023 = (
    df[(df["Type"] == "Domestic") & (df["Year"] == 2023)]
    .groupby("Airline")["Total Passengers"]
    .sum()
    .sort_values(ascending=False)
)

chart = ElegantChart(
    title="Trans Maldivian Dominates\nDomestic Skies",
    subtitle="Domestic passengers by airline, 2023",
    caption="Source: Maldives Bureau of Statistics\nData Visualized by Hassan Shammu",
    theme="newsroom_dark",
)

chart.bar(
    x=domestic_2023.index.tolist(),
    ys=domestic_2023.tolist(),
    labels=["Total Passengers"],
    horizontal=True,
    show_value_labels=True,
    y_formatter="compact",
    max_label_width=20,
    label_width_strategy="truncate",
    show=False,
    save_path="series_101_domestic_airlines_2023.png",
)
