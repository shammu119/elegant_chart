# Diagnostic: measure top margin (above title) and bottom margin (below
# footer/caption/logo) on the REAL occupancy_rates example.
import matplotlib.pyplot as plt
import pandas as pd
from statsmodels.tsa.seasonal import STL

from elegant_chart import ElegantChart
from elegant_chart.get_api_data import get_series_df

SERIES = {
    "Resorts": 219,
    "Hotels": 218,
    "Safari Vessel": 220,
    "Guesthouse": 217,
}

frames = []
for label, sid in SERIES.items():
    df = get_series_df(sid)
    date_col = next((c for c in df.columns if "date" in c.lower() or "period" in c.lower()), df.columns[0])
    val_col = next((c for c in df.columns if c.lower() in {"amount", "value", "val"}), df.columns[-1])
    frames.append(df[[date_col, val_col]].rename(columns={date_col: "date", val_col: label}).set_index("date"))

merged = pd.concat(frames, axis=1).reset_index()
merged["date"] = pd.to_datetime(merged["date"])
merged = merged.sort_values("date").reset_index(drop=True)
present_labels = [label for label in SERIES if label in merged.columns]
merged = merged.dropna(subset=present_labels, how="any")

for label in present_labels:
    series = merged.set_index("date")[label]
    result = STL(series, period=12, robust=True).fit()
    merged[label] = (series - result.seasonal).to_numpy()

x = merged["date"].tolist()
ys = {label: merged[label].tolist() for label in SERIES if label in merged.columns}

chart = ElegantChart(
    title="Resorts rule, but guesthouses\nare catching up?",
    subtitle="Occupancy %, 2010–2026",
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
)

fig, ax = chart.line(
    x=x,
    ys=ys,
    markers=False,
    linewidth=1,
    alpha_map={"Resorts": 0.3, "Guesthouse": 1, "Hotels": 0.3, "Safari Vessel": 0.3},
    y_formatter=lambda x, pos: f"{x * 100:.0f}",
    show=False,
    save_path="tmp_render.png",
    x_year_tick_interval=5,
    x_upper_pad=0.09,
)

fig.canvas.draw()
renderer = fig.canvas.get_renderer()
fig_h = fig.get_size_inches()[1] * fig.dpi
PT_PER_FRAC = fig.get_size_inches()[1] * 72

print(f"subplotpars: top={fig.subplotpars.top:.4f} bottom={fig.subplotpars.bottom:.4f}")
print(f"baseline_relocated={getattr(chart, '_baseline_relocated', None)}")

# Title: topmost text (highest y1)
max_y1 = None
top_artist = None
for artist in fig.findobj(match=plt.Text):
    txt = artist.get_text().strip()
    if not txt:
        continue
    bb = artist.get_window_extent(renderer)
    y1_frac = bb.y1 / fig_h
    if max_y1 is None or y1_frac > max_y1:
        max_y1 = y1_frac
        top_artist = txt[:30]

print(f"topmost artist: {top_artist!r} y1={max_y1:.4f}")
top_gap_frac = 1.0 - max_y1
print(f"TOP GAP (fig top -> topmost artist) = {top_gap_frac:.4f} fig-frac = {top_gap_frac*PT_PER_FRAC:.2f}pt")

# Bottom: list all artists with y0 < 0.08, with visibility, for inspection
print("--- artists near bottom (y0 < 0.08) ---")
for artist in fig.findobj(match=plt.Text):
    txt = artist.get_text().strip()
    if not txt:
        continue
    bb = artist.get_window_extent(renderer)
    y0_frac, y1_frac = bb.y0 / fig_h, bb.y1 / fig_h
    if y0_frac < 0.08:
        print(f"  Text {txt[:35]!r} visible={artist.get_visible()} y0={y0_frac:.4f} y1={y1_frac:.4f} alpha={artist.get_alpha()}")

for a in fig.axes:
    if a is ax:
        continue
    bb = a.get_window_extent(renderer)
    y0_frac, y1_frac = bb.y0 / fig_h, bb.y1 / fig_h
    print(f"  Axes(logo) y0={y0_frac:.4f} y1={y1_frac:.4f}")

for artist in fig.findobj(match=plt.Text):
    txt = artist.get_text()
    if "Source" in txt:
        bb = artist.get_window_extent(renderer)
        y0_frac, y1_frac = bb.y0 / fig_h, bb.y1 / fig_h
        print(f"  Caption block: y0={y0_frac:.4f} ({y0_frac*PT_PER_FRAC:.2f}pt) y1={y1_frac:.4f} ({y1_frac*PT_PER_FRAC:.2f}pt)")

tight_bb = fig.get_tightbbox(renderer)
print(f"tight bbox: y0={tight_bb.y0/fig_h:.4f} y1={tight_bb.y1/fig_h:.4f}")

# Above-footer gap: lowest visible x-tick label vs footer_line_y
footer_line_y = fig.subplotpars.bottom if getattr(chart, "_baseline_relocated", False) else 0.0666
min_label_y0 = None
for lbl in ax.get_xticklabels():
    if not lbl.get_text().strip():
        continue
    bb = lbl.get_window_extent(renderer)
    y0_frac = bb.y0 / fig_h
    if min_label_y0 is None or y0_frac < min_label_y0:
        min_label_y0 = y0_frac
gap = min_label_y0 - footer_line_y
print(f"footer_line_y={footer_line_y:.4f} lowest xtick label y0={min_label_y0:.4f}")
print(f"ABOVE-FOOTER GAP = {gap:.4f} fig-frac = {gap*PT_PER_FRAC:.2f}pt")
