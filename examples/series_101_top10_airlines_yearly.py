# examples/series_101_top10_airlines_yearly.py
"""
Bump chart: top 5 airlines by international passenger volume at VIA,
ranked year-by-year from 2020 to 2023.

Run from the project root:
    python examples/series_101_top10_airlines_yearly.py
"""

import pandas as pd

from elegant_chart import ElegantChart

# ── load & filter ──────────────────────────────────────────────────────────────
df = pd.read_excel("data/series_101.xlsx")

intl = df[(df["Type"] == "International") & (df["Airline"] != "International Non-Scheduled")]

# ── yearly totals per airline ──────────────────────────────────────────────────
yearly = (
    intl.groupby(["Year", "Airline"])["Total Passengers"]
    .sum()
    .reset_index()
    .rename(columns={"Total Passengers": "Passengers"})
)
years = sorted(yearly["Year"].unique())

# ── pick the top 5 airlines by combined 2020-2023 passenger count ──────────────
top10_airlines = (
    yearly.groupby("Airline")["Passengers"]
    .sum()
    .sort_values(ascending=False)
    .head(5)
    .index.tolist()
)

# ── pivot into {airline: [passengers_2020, …, passengers_2023]} ───────────────
pivot = (
    yearly[yearly["Airline"].isin(top10_airlines)]
    .pivot(index="Airline", columns="Year", values="Passengers")
    .reindex(index=top10_airlines, columns=years)
)

ys = {airline: pivot.loc[airline].tolist() for airline in top10_airlines}

# ── all 5 are heroes: distinct palette colors, no grey hierarchy ───────────────
# IATA codes for airline logos
IATA_CODES = {
    "Emirates": "EK",
    "Qatar Airways": "QR",
    "IndiGo": "6E",
    "Aeroflot": "SU",
    "SriLankan Airlines": "UL",
}

label_logos = {
    airline: f"logo/iata_codes/{code}.png"
    for airline, code in IATA_CODES.items()
    if airline in top10_airlines
}

# ── chart — short figsize for tight editorial rank spacing ─────────────────────
# figsize=(2.16, 1.60) → 1080×800px at 500 DPI.
# font_scale=1.5 compensates for the reduced _figure_scale (0.356 vs 0.6 default)
# so rendered font sizes stay proportional to the standard chart.
chart = ElegantChart(
    title="Skies of the Maldives:\nAirline Rankings at VIA",
    subtitle="Ranked by annual passengers carried",
    caption="Source: Maldives Bureau of Statistics\nData Visualized by Hassan Shammu\n",
    theme="newsroom_dark",
    # figsize=(2.16, 1.60),
    # font_scale=1.5,
)

BRAND_COLORS = {
    "Emirates": "#d11a3a",  # Emirates crimson red
    "Qatar Airways": "#7e224d",  # Qatar maroon
    "IndiGo": "#0082ba",  # IndiGo sky blue (light, from livery)
    "SriLankan Airlines": "#239a45",  # SriLankan peacock green
    "Aeroflot": "#1d4ed8",  # Aeroflot dark navy
}

chart.bump(
    x=years,
    ys=ys,
    ascending=False,
    highlight=top10_airlines,  # all 5 are heroes — no grey ghost lines
    highlight_colors=BRAND_COLORS,
    show_labels=True,
    label_logos=label_logos,
    label_display={
        "SriLankan Airlines": "SriLankan\nAirlines",
        "Qatar Airways": "Qatar\nAirways",
    },
    show=False,
    save_path="series_101_top10_airlines_yearly.png",
    export_xlsx=False,
)
