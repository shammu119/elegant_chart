import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd
from elegant_chart.get_api_data import get_series_df
from elegant_chart import ElegantChart

SERIES = {
    "Guesthouse": 217,
    "Hotels": 218,
    "Resorts": 219,
    "Safari Vessel": 220,
}

# ── Fetch & merge ─────────────────────────────────────────────────────────────
frames = []
for label, sid in SERIES.items():
    df = get_series_df(sid)
    if df.empty:
        print(f"Warning: no data returned for {label} (id={sid})")
        continue

    # Detect the date/period and value columns
    date_col = next(
        (c for c in df.columns if "date" in c.lower() or "period" in c.lower()),
        df.columns[0],
    )
    val_col = next(
        (c for c in df.columns if c.lower() in {"amount", "value", "val"}),
        df.columns[-1],
    )

    frames.append(
        df[[date_col, val_col]].rename(columns={date_col: "date", val_col: label}).set_index("date")
    )

merged = pd.concat(frames, axis=1).reset_index()
merged["date"] = pd.to_datetime(merged["date"])
merged = merged.sort_values("date").reset_index(drop=True)

# Keep only dates where all present series have data
present_labels = [label for label in SERIES if label in merged.columns]
merged = merged.dropna(subset=present_labels, how="any")

x = merged["date"].tolist()
ys = {label: merged[label].tolist() for label in SERIES if label in merged.columns}

# ── Plot ──────────────────────────────────────────────────────────────────────
chart = ElegantChart(
    title="Occupancy Rates by Accommodation Type",
    subtitle="Source: Maldives Monetary Authority",
    ylabel="Occupancy Rate",
)

chart.line(
    x=x,
    ys=ys,
    markers=False,
    linewidth=1,
    y_formatter="plain",
    show=False,
    save_path="occupancy_rates.png",
)
