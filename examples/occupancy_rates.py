# examples/occupancy_rates.py
"""
Live-data line() example — fetches accommodation occupancy rates from the
MMA Statistics API and plots them as a multi-series line chart.

Self-contained: copy this whole file and run it as-is, with `elegant_chart`
installed (`pip install -e .`). Requires network access; responses are
cached under `data/` (see `elegant_chart.get_api_data`).
"""

import pandas as pd
from statsmodels.tsa.seasonal import STL

from elegant_chart import ElegantChart, enable_logging
from elegant_chart.get_api_data import get_series_df

enable_logging()

SERIES = {
    "Resorts": 219,
    "Hotels": 218,
    "Safari Vessel": 220,
    "Guesthouse": 217,
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

# ── Seasonal adjustment ─────────────────────────────────────────────────────
# Remove the recurring yearly pattern (e.g. holiday-season peaks) via STL,
# leaving the trend + residual so underlying changes in occupancy are clearer.
SEASONALLY_ADJUST = True
if SEASONALLY_ADJUST:
    for label in present_labels:
        series = merged.set_index("date")[label]
        result = STL(series, period=12, robust=True).fit()
        merged[label] = (series - result.seasonal).to_numpy()

x = merged["date"].tolist()
ys = {label: merged[label].tolist() for label in SERIES if label in merged.columns}

# ── Plot ──────────────────────────────────────────────────────────────────────
chart = ElegantChart(
    title="Resorts Still Lead but\nGuesthouses Gain Ground",
    subtitle="Occupancy % 2010–2026",
    caption="Source: Maldives Monetary Authority (MMA) Statistics API\nNote: Data is monthly, seasonally adjusted\nData Visualized by Hassan Shammu",
    theme="newsroom_dark",
    align_x_edges=False,
    y_tick_labels_inside=True,
    color_map={
        "Resorts": "#E8742A",
        "Guesthouse": "#64D2FF",
        "Hotels": "#A78BFA",
        "Safari Vessel": "#34D399",
    },
    legend_ncol=4,
)

chart.line(
    x=x,
    ys=ys,
    markers=False,
    linewidth=1,
    alpha_map={
        "Resorts": 0.3,
        "Guesthouse": 1,
        "Hotels": 0.3,
        "Safari Vessel": 0.3,
    },
    y_formatter=lambda x, pos: f"{x * 100:.0f}",
    # ylim=(0, 1),
    show=False,
    save_path="occupancy_rates.png",
    x_year_tick_interval=5,
    x_upper_pad=0.09,
)
