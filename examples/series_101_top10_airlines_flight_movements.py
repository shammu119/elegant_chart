# examples/series_101_top10_airlines_flight_movements.py
"""
Top 10 airlines by flight movements, 2021-2023 combined - bar chart built
from data/series_101.xlsx.
"""

import pandas as pd

from elegant_chart import ElegantChart

df = pd.read_excel("data/series_101.xlsx")

top10 = (
    df[(df["Type"] == "International") & (df["Airline"] != "International Non-Scheduled")]
    .groupby("Airline")["Flight Movements"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

chart = ElegantChart(
    title="Traffic in Paradise:VIA's\nBusiest Airlines",
    subtitle="Air traffic movements, 2020–23 combined",
    caption="Source: Maldives Bureau of Statistics\nData Visualized by Hassan Shammu\n",
    theme="newsroom_dark",
    color_map={"Flight Movements": "#64D2FF"},
)

# IATA codes for the top 10 airlines, used to pick logos from logo/iata_codes/.
airline_iata_codes = {
    "Emirates": "EK",
    "Qatar Airways": "QR",
    "IndiGo": "6E",
    "SriLankan Airlines": "UL",
    "flydubai": "FZ",
    "Maldivian": "Q2",
    "Turkish Airlines": "TK",
    "Gulf Air": "GF",
    "Singapore Airlines": "SQ",
    "GoFirst": "G8",
}
y_tick_logos = {
    airline: f"logo/iata_codes/{code}.png" for airline, code in airline_iata_codes.items()
}

chart.bar(
    x=top10.index.tolist(),
    ys=top10.tolist(),
    labels=["Flight Movements"],
    horizontal=True,
    show_value_labels=True,
    y_formatter="compact",
    max_label_width=20,
    label_width_strategy="truncate",
    y_tick_logos=y_tick_logos,
    show=False,
    save_path="series_101_top10_airlines_flight_movements.png",
)
