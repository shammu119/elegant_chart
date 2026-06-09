# elegant_chart — Usage Guide

## Contents

1. [Installation](#1-installation)
2. [Your first chart](#2-your-first-chart)
3. [Bar charts](#3-bar-charts)
4. [Line charts](#4-line-charts)
5. [Themes](#5-themes)
6. [DataFrame input](#6-dataframe-input)
7. [Y-axis formatting](#7-y-axis-formatting)
8. [Axis limits and tick control](#8-axis-limits-and-tick-control)
9. [X-axis label control](#9-x-axis-label-control)
10. [Title, subtitle, labels, caption](#10-title-subtitle-labels-caption)
11. [Saving charts](#11-saving-charts)
12. [Exporting data to Excel](#12-exporting-data-to-excel)
13. [Font notes](#13-font-notes)
14. [MMA Statistics API helper](#14-mma-statistics-api-helper)
15. [Extending with custom mixins](#15-extending-with-custom-mixins)
16. [Error reference](#16-error-reference)

---

## 1. Installation

```bash
# From GitHub
pip install git+https://github.com/shammu119/elegant_chart.git

# Editable install (for development)
git clone https://github.com/shammu119/elegant_chart.git
cd elegant_chart
pip install -e ".[dev]"

# With the MMA data helper (adds requests + openpyxl)
pip install "elegant_chart[data]"
```

---

## 2. Your first chart

```python
from elegant_chart import ElegantChart

chart = ElegantChart(title="Monthly Revenue")
chart.bar(
    x=["Jan", "Feb", "Mar", "Apr"],
    ys=[120_000, 145_000, 132_000, 168_000],
    show=True,
)
```

`ElegantChart` holds your chart configuration (theme, labels, axis settings). Calling
`.bar()` or `.line()` on it renders the chart and optionally displays or saves it.

Both methods return `(fig, ax)` — a standard matplotlib `Figure` and `Axes` pair — so
you can do any further customisation after the call.

---

## 3. Bar charts

### 3.1 Single series — categorical x

```python
chart = ElegantChart(title="Sales by Region")
chart.bar(
    x=["North", "South", "East", "West"],
    ys=[430, 310, 520, 280],
)
```

### 3.2 Single series — numeric x

Pass numbers directly; the x axis becomes continuous.

```python
chart = ElegantChart(title="Annual Growth")
chart.bar(
    x=[2019, 2020, 2021, 2022, 2023],
    ys=[3.1, -0.8, 5.4, 4.2, 3.7],
    y_formatter="plain",
)
```

### 3.3 Single series — datetime x

Pass `datetime` objects or `pandas.Timestamp` values; the axis auto-formats.

```python
from datetime import datetime

chart = ElegantChart(title="Weekly Traffic")
chart.bar(
    x=[datetime(2024, 1, 7), datetime(2024, 1, 14), datetime(2024, 1, 21)],
    ys=[14_200, 16_800, 15_500],
)
```

### 3.4 Multi-series — grouped bars (default)

Pass a list of lists. Each inner list is one series. Provide `labels` for a legend.

```python
chart = ElegantChart(title="Revenue vs Costs")
chart.bar(
    x=["Q1", "Q2", "Q3", "Q4"],
    ys=[
        [120_000, 145_000, 132_000, 168_000],  # Revenue
        [ 85_000,  92_000,  88_000,  95_000],  # Cost
    ],
    labels=["Revenue", "Cost"],
)
```

### 3.5 Multi-series — stacked bars

```python
chart = ElegantChart(title="Product Mix")
chart.bar(
    x=["Jan", "Feb", "Mar", "Apr"],
    ys={
        "Product A": [40, 55, 48, 62],
        "Product B": [30, 28, 35, 40],
        "Product C": [15, 20, 18, 25],
    },
    stacked=True,
)
```

> **Tip:** you can pass `ys` as a `dict` — keys become the series labels automatically,
> so you don't need to also pass `labels`.

### 3.6 Bar width

```python
# Narrower bars (more white space between groups)
chart.bar(x=["A", "B", "C"], ys=[1, 2, 3], bar_width=0.4)

# Full-width bars (no gap — suits dense histograms)
chart.bar(x=["A", "B", "C"], ys=[1, 2, 3], bar_width=1.0)
```

---

## 4. Line charts

### 4.1 Single series

```python
chart = ElegantChart(title="Inflation Rate", ylabel="CPI %")
chart.line(
    x=["Jan", "Feb", "Mar", "Apr", "May"],
    ys=[3.2, 3.5, 3.8, 3.6, 3.4],
    y_formatter="plain",
)
```

### 4.2 Without markers

```python
chart.line(
    x=list(range(2000, 2025)),
    ys=[...],          # 25 data points
    markers=False,     # cleaner for dense series
    linewidth=1.5,
)
```

### 4.3 Multi-series

```python
chart = ElegantChart(title="Export Indicators")
chart.line(
    x=["2019", "2020", "2021", "2022", "2023"],
    ys={
        "Fish":    [412, 388, 445, 502, 521],
        "Tourism": [1800, 320, 1100, 1650, 1920],
    },
    compact_years=True,   # "2019", "20", "21", "22", "23"
)
```

### 4.4 Datetime x axis

```python
import pandas as pd

dates = pd.date_range("2020-01", periods=12, freq="MS")

chart = ElegantChart(title="Monthly Deposits (MVR)")
chart.line(
    x=dates,
    ys=[980, 1020, 1100, 1050, 1150, 1200, 1180, 1250, 1300, 1280, 1350, 1400],
)
```

---

## 5. Themes

Four built-in themes are available. Pass `theme=` to the constructor.

```python
# Light themes
ElegantChart(theme="consulting_light")  # default — white background
ElegantChart(theme="newsroom_muted")    # off-white, muted tones

# Dark themes
ElegantChart(theme="consulting_dark")   # dark navy background
ElegantChart(theme="newsroom_dark")     # near-black, cyan/teal palette
```

Example — dark theme with a title:

```python
chart = ElegantChart(
    title="GDP Growth",
    subtitle="Real annual growth rate, %",
    theme="consulting_dark",
)
chart.bar(
    x=["2019", "2020", "2021", "2022", "2023"],
    ys=[7.5, -6.3, 18.9, 13.5, 6.0],
    y_formatter="plain",
    compact_years=True,
)
```

---

## 6. DataFrame input

Instead of extracting columns manually, pass the DataFrame directly.

### Single y column

```python
import pandas as pd
from elegant_chart import ElegantChart

df = pd.DataFrame({
    "quarter": ["Q1 23", "Q2 23", "Q3 23", "Q4 23"],
    "revenue": [12.4, 14.1, 13.8, 16.2],
})

chart = ElegantChart(title="Quarterly Revenue (MVR M)")
chart.bar(df=df, x_col="quarter", y_cols="revenue")
```

### Multiple y columns

```python
df = pd.DataFrame({
    "year":   [2020, 2021, 2022, 2023],
    "exports": [1.2, 1.8, 2.1, 2.4],
    "imports": [2.8, 3.0, 3.3, 3.1],
})

chart = ElegantChart(title="Trade Balance (USD B)")
chart.line(df=df, x_col="year", y_cols=["exports", "imports"])
```

When using `df=`, the column names become the series labels automatically.

---

## 7. Y-axis formatting

Control how y-axis tick values are displayed with `y_formatter`.

### Built-in formatters

```python
# "compact" (default) — abbreviates large numbers
# 1500 → "1.5K",  2_400_000 → "2.4M",  1_300_000_000 → "1.3B"
chart.bar(x=["A", "B"], ys=[1_500_000, 2_400_000])

# "plain" — standard Python number formatting (no abbreviation)
chart.bar(x=["A", "B"], ys=[3.14, 2.71], y_formatter="plain")

# "percent" — multiplies by 100 and appends %
# 0.123 → "12.3%"
chart.bar(x=["A", "B"], ys=[0.45, 0.72], y_formatter="percent")
```

### Normalise by maximum value

`("norm_max", decimals)` divides each tick by the series maximum, showing values
as a fraction of the peak. Useful for indexed series.

```python
from elegant_chart import YFormatter

chart.bar(
    x=["2019", "2020", "2021", "2022"],
    ys=[850, 690, 920, 1000],
    y_formatter=(YFormatter.NORM_MAX, 2),  # e.g. "0.85", "0.69", "0.92", "1"
)
```

### Custom format string

Any Python format string using `{x}` is accepted.

```python
chart.bar(
    x=["Jan", "Feb", "Mar"],
    ys=[3.14, 2.71, 1.62],
    y_formatter="{x:.2f}",
)
```

### Custom callable

For full control, pass any `(value, position) -> str` function.

```python
def mvr_formatter(value, pos):
    return f"MVR {value:,.0f}"

chart.bar(
    x=["Q1", "Q2", "Q3"],
    ys=[120_000, 145_000, 132_000],
    y_formatter=mvr_formatter,
)
```

### Y-axis constructor defaults

Set `y_formatter` once on the constructor so every chart uses it.

```python
chart = ElegantChart(
    title="All charts use MVR format",
    y_formatter=mvr_formatter,
)
chart.bar(x=["Q1", "Q2"], ys=[100_000, 120_000])
chart.line(x=["Q1", "Q2"], ys=[100_000, 120_000])
```

---

## 8. Axis limits and tick control

### Y-axis

```python
# Fixed tick spacing (a tick every 500 units)
chart.bar(x=["A", "B", "C"], ys=[1000, 2000, 1500], y_tick_step=500)

# Cap the number of ticks
chart.bar(x=["A", "B", "C"], ys=[1000, 2000, 1500], max_y_ticks=4)

# Fix the y-axis range
chart.bar(x=["A", "B", "C"], ys=[1000, 2000, 1500], ylim=(0, 2500))
```

`ylim` can also be set on the constructor to apply as a global default.

### X-axis — numeric

```python
chart.bar(
    x=[2010, 2011, 2012, 2013, 2014, 2015],
    ys=[...],
    x_tick_step=2,          # tick every 2 years: 2010, 2012, 2014
)

chart.bar(
    x=[2010, 2011, 2012, 2013, 2014, 2015],
    ys=[...],
    xlim=(2011, 2014),      # zoom into a range
)
```

### X-axis — categorical thinning

When you have many categorical labels, the library auto-thins them to avoid overlap.
You can also control this explicitly.

```python
# Show every 3rd label
chart.bar(x=years_list, ys=values, x_tick_step=3)

# Cap at 6 visible labels (library picks the step)
chart.bar(x=years_list, ys=values, max_x_ticks=6)

# Disable auto-thinning entirely
chart.bar(x=short_list, ys=values, auto_x_thinning=False)
```

---

## 9. X-axis label control

### Rotate labels

```python
chart.bar(
    x=["January", "February", "March", "April", "May", "June"],
    ys=[10, 12, 9, 14, 11, 13],
    rotation=45,
)
```

### Wrap or truncate long labels

```python
# Wrap at 8 characters (splits into multiple lines)
chart.bar(
    x=["Short", "A Very Long Label", "Another Long One"],
    ys=[1, 2, 3],
    max_label_width=8,
    label_width_strategy="wrap",    # default
)

# Truncate with ellipsis instead
chart.bar(
    x=["Short", "A Very Long Label", "Another Long One"],
    ys=[1, 2, 3],
    max_label_width=10,
    label_width_strategy="truncate",
)
```

### Compact year labels

When x labels are years, `compact_years=True` abbreviates all but the first:
`["2020", "2021", "2022", "2023"]` → `["2020", "21", "22", "23"]`.

```python
chart.bar(
    x=["2019", "2020", "2021", "2022", "2023"],
    ys=[7.5, -6.3, 18.9, 13.5, 6.0],
    compact_years=True,
)
```

> **Note:** `compact_years` defaults to `False`. Do not enable it for non-year
> integer labels (e.g. product codes `[1001, 1002]`) — it would corrupt them.

---

## 10. Title, subtitle, labels, caption

All text fields are set on the constructor.

```python
chart = ElegantChart(
    title="Maldives Tourism Arrivals",
    subtitle="Annual visitor arrivals, 2015–2023",
    xlabel="Year",
    ylabel="Arrivals",      # shown on the right-hand y axis
    caption="Source: Maldives Immigration, 2024",
    figsize=(10, 6),        # width × height in inches
    font_scale=1.1,         # scale all font sizes by this factor
)
chart.bar(
    x=["2015", "2016", "2017", "2018", "2019", "2020", "2021", "2022", "2023"],
    ys=[1_234_248, 1_286_135, 1_389_542, 1_484_274, 1_702_887,
        555_494, 1_323_624, 1_675_819, 1_874_965],
    compact_years=True,
)
```

### Logo in the footer

By default the chart looks for a logo at `~/logo/ce_logo.png`. Override with:

```python
chart = ElegantChart(
    title="Report Chart",
    caption="Prepared by Analytics Team",
    logo_path="assets/company_logo.png",
    logo_height_rel=0.10,   # logo height as a fraction of figure height
    logo_margin_rel=0.02,   # right margin
)
```

If the logo file doesn't exist the footer renders without it — no error is raised.

---

## 11. Saving charts

### Save by passing `save_path`

The format is inferred from the file extension.

```python
chart.bar(
    x=["A", "B", "C"],
    ys=[1, 2, 3],
    show=False,             # don't open a window, just save
    save_path="output/chart.png",
    save_dpi=500,           # default is 500 for high-quality export
)
```

Supported formats: anything matplotlib supports — `png`, `pdf`, `svg`, `eps`.

```python
# Save as PDF (vector — ideal for print)
chart.bar(x=..., ys=..., show=False, save_path="chart.pdf")

# Save as SVG (vector — ideal for web)
chart.bar(x=..., ys=..., show=False, save_path="chart.svg")
```

### Save using the returned Figure

```python
fig, ax = chart.bar(x=..., ys=..., show=False)
fig.savefig("custom_output.png", dpi=300, bbox_inches="tight")
```

### Save and show

```python
chart.bar(
    x=...,
    ys=...,
    show=True,              # open interactive window AND save
    save_path="chart.png",
)
```

---

## 12. Exporting data to Excel

After any `bar()` or `line()` call, `export_data()` writes the underlying data to
an `.xlsx` file. The sheet has one column per series plus an `x` column.

```python
chart = ElegantChart(title="Trade Data")
chart.bar(
    x=["2020", "2021", "2022", "2023"],
    ys={
        "Exports": [1.2, 1.8, 2.1, 2.4],
        "Imports": [2.8, 3.0, 3.3, 3.1],
    },
    show=False,
)
chart.export_data("trade_data.xlsx")
# Produces: | x    | Exports | Imports |
#           | 2020 |     1.2 |     2.8 |
#           | 2021 |     1.8 |     3.0 |
#           | ...  |     ... |     ... |
```

`export_data()` always reflects the **most recent** render on that instance:

```python
chart.bar(x=["A", "B"], ys=[1, 2], show=False)
chart.line(x=["X", "Y", "Z"], ys=[9, 8, 7], show=False)  # replaces previous
chart.export_data("latest.xlsx")  # contains X, Y, Z data — not A, B
```

Requires `openpyxl` (included in `pip install "elegant_chart[data]"`).

---

## 13. Font notes

`elegant_chart` is designed to use Apple's **SF Pro** typeface. If the font files
are not present, the library falls back to the system sans-serif and emits a
`UserWarning`:

```
UserWarning: SF Pro fonts not found — falling back to system sans-serif.
Place SF Pro .ttf/.otf files in a fonts/ directory to use them.
```

To use SF Pro, place the font files in a `fonts/` directory relative to your
working directory:

```
your_project/
├── fonts/
│   ├── SF-Pro.ttf
│   ├── SF-Pro-Display-Light.otf
│   ├── SF-Pro-Display-Medium.otf
│   └── SF-Pro-Text-Bold.otf
└── your_script.py
```

To suppress the warning when using a different font intentionally:

```python
import warnings
warnings.filterwarnings("ignore", message="SF Pro fonts not found")

chart = ElegantChart(...)
```

---

## 14. MMA Statistics API helper

Requires the `data` extras group:

```bash
pip install "elegant_chart[data]"
```

### Authentication

The bearer token is **never hardcoded**. Provide it one of two ways:

**Option A — environment variable (preferred for scripts and CI):**

```bash
export MMA_API_TOKEN="your_token_here"
python your_script.py
```

**Option B — `TOKEN.txt` (for local interactive use):**

Create a plain text file containing only the token:

```
your_token_here
```

`TOKEN.txt` is listed in `.gitignore` and will never be committed.

> ⚠️ Never put a token directly in source code or commit it to git.

### Fetching a series

```python
from elegant_chart.get_api_data import get_series_df

# Fetch series ID 2307 from database.mma.gov.mv
df = get_series_df(2307)
print(df.head())

# Optionally save to Excel
df.to_excel("series_2307.xlsx", index=False)
```

### Full workflow — fetch, chart, export

```python
from elegant_chart import ElegantChart
from elegant_chart.get_api_data import get_series_df

df = get_series_df(2307)

chart = ElegantChart(
    title="MMA Series 2307",
    subtitle="Source: database.mma.gov.mv",
    theme="consulting_light",
)
chart.line(
    df=df,
    x_col="date",
    y_cols="value",
    show=True,
    save_path="series_2307.png",
)
chart.export_data("series_2307.xlsx")
```

---

## 15. Extending with custom mixins

Because `ElegantChart` is assembled from mixins on top of `ChartBase`, you can add
new chart types by writing a mixin and composing it in.

```python
import matplotlib.pyplot as plt
from matplotlib import rc_context
from elegant_chart import ElegantChart
from elegant_chart.base import ChartBase


class ScatterMixin:
    """Adds a scatter() method using the same palette and styling as bar/line."""

    def scatter(self, x, y, label=None, show=True, save_path=None, save_dpi=500):
        with rc_context(self._rc):
            fig, ax = self._init_figure_and_axes()
            self._configure_grid(ax)

            color = self.palette[0]
            ax.scatter(x, y, color=color, label=label, zorder=2)

            self._apply_axis_limits(ax, None, None)
            self._apply_y_axis(ax)
            self._finalize_axes(ax, has_legend=bool(label))
            self._add_footer(fig)

            if save_path:
                self.save_figure(fig, save_path, dpi=save_dpi)
            if show:
                plt.show()

            return fig, ax


class MyChart(ScatterMixin, ElegantChart):
    """ElegantChart extended with scatter support."""
    pass


chart = MyChart(title="Scatter Example", theme="consulting_dark")
chart.scatter(x=[1, 2, 3, 4, 5], y=[2, 4, 1, 5, 3])
```

All attributes from `ChartBase` (`self.palette`, `self._rc`, `self.bg_color`, etc.)
are available inside your mixin without any extra setup — they are guaranteed by the
contract defined in `base.py`.

---

## 16. Error reference

| Error | Cause | Fix |
|-------|-------|-----|
| `ValueError: x must not be empty` | `x=[]` passed to `bar`/`line` | Provide at least one x value |
| `ValueError: Series 'name' length N does not match x length M` | `ys` and `x` have different lengths | Ensure every series has the same length as `x` |
| `ValueError: ys contains non-finite values` | A `NaN` or `inf` in the data | Clean data before charting (`df.dropna()`) |
| `ValueError: ys must be provided` | Called `bar(x=...)` without `ys` or `df` | Pass `ys=` or use `df=` with `x_col` and `y_cols` |
| `ValueError: If df is provided, x_col and y_cols must be set` | `df=` passed without column names | Always pair `df=` with `x_col=` and `y_cols=` |
| `RuntimeError: No chart data to export` | `export_data()` called before `bar()`/`line()` | Call a chart method first |
| `ImportError: openpyxl is required` | `export_data()` or `.to_excel()` without openpyxl | `pip install "elegant_chart[data]"` |
| `RuntimeError: MMA API token not found` | `get_series_df()` called without token | Set `MMA_API_TOKEN` env var or create `TOKEN.txt` |
| `UserWarning: SF Pro fonts not found` | SF Pro not installed | Install fonts into `fonts/` or suppress the warning (see §13) |
