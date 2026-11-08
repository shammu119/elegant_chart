# elegant_chart

A lightweight and flexible charting toolkit built in Python. The project uses a modular mixin
architecture that allows you to create customisable charts with clean and extensible code.

> **New here?** Start with the step-by-step [guides](docs/guides/README.md). You'll
> make your first chart in Chart Studio, the point-and-click app, in about 10 minutes.

## Features

- Modular system using mixins (axis, bar, line, style, figure, data)
- Categorical, numeric, and datetime x-axis support
- Four built-in themes: `consulting_light`, `consulting_dark`, `newsroom_muted`, `newsroom_dark`
- Multi-series, grouped, and stacked bar charts
- Strong typing for predictable and maintainable behaviour
- Optional helper for retrieving data from the MMA Statistics API

## Installation

### Install directly from GitHub

```bash
pip install git+https://github.com/shammu119/elegant_chart.git
```

### Editable install (recommended during development)

```bash
git clone https://github.com/shammu119/elegant_chart.git
cd elegant_chart
pip install -e ".[dev]"
```

## Quick Start

```python
from elegant_chart import ElegantChart

# Bar chart
chart = ElegantChart(title="Quarterly Revenue", theme="consulting_light")
chart.bar(
    x=["Q1", "Q2", "Q3", "Q4"],
    ys=[120, 145, 132, 168],
    show=True,
)
```

```python
# Line chart — multi-series with a legend
chart = ElegantChart(title="Sales vs Costs", subtitle="FY 2024")
chart.line(
    x=["Jan", "Feb", "Mar", "Apr"],
    ys=[[100, 115, 108, 130], [80, 90, 88, 95]],
    labels=["Revenue", "Cost"],
    show=True,
)
```

```python
# Using a DataFrame
import pandas as pd

df = pd.DataFrame({"month": ["Jan", "Feb", "Mar"], "sales": [100, 120, 90]})
chart = ElegantChart(title="Monthly Sales")
chart.bar(df=df, x_col="month", y_cols="sales", show=True)
```

## Themes

| Name | Style |
|------|-------|
| `consulting_light` (default) | White background, professional palette |
| `consulting_dark` | Dark navy background, bright palette |
| `newsroom_muted` | Off-white background, muted tones |
| `newsroom_dark` | Near-black background, cyan/teal palette |

```python
chart = ElegantChart(theme="consulting_dark")
```

## Key Parameters

### Constructor (`ElegantChart(...)`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `title` | `None` | Chart title |
| `subtitle` | `None` | Subtitle shown below the title |
| `theme` | `"consulting_light"` | Visual theme |
| `dpi` | `150` | Screen DPI (saving uses `save_dpi=500`) |
| `figsize` | `(2.16, 2.7)` | Figure size in inches. Default × `save_dpi=500` → **1080×1350 px**. All fonts and geometric elements auto-scale proportionally on override. |
| `y_formatter` | `"compact"` | Y-axis number format (`"compact"`, `"plain"`, `"percent"`) |

### `bar()` / `line()` shared parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `x` | — | X values (strings, numbers, or `datetime` objects) |
| `ys` | — | Y values: a list, list-of-lists, or `{"label": values}` dict |
| `labels` | `None` | Series labels for the legend |
| `df` | `None` | Pass a DataFrame; also set `x_col` and `y_cols` |
| `compact_years` | `False` | Abbreviate year labels (e.g. `"2020", "21", "22"`) |
| `show` | `True` | Call `plt.show()` after rendering |
| `save_path` | `None` | Save to file (format inferred from extension) |
| `save_dpi` | `500` | DPI used when saving |

## MMA Data Helper (optional)

Requires the `data` extras:

```bash
pip install "elegant_chart[data]"
```

Store your bearer token in a **gitignored** `TOKEN.txt` file (one line, the token only) or set the
`MMA_API_TOKEN` environment variable. Never commit the token.

```python
from elegant_chart.get_api_data import get_series_df

# Loads from data/series_2307.xlsx when available, otherwise fetches from the API
# and caches the result to that file for future calls.
df = get_series_df(2307)
df.to_excel("data.xlsx", index=False)
```

## Chart Studio (GUI, optional)

A local, single-user app for going from raw data to a finished chart without
writing code. See the [getting started guide](docs/guides/01-getting-started.md). A toolbar (chart type, export) sits on top of three panels:
**checklist, data and reshaping** on the left, a **live preview** in the centre, and an
**inspector** with one settings section at a time on the right.

```bash
pip install -e ".[app]"
elegant-chart-studio            # or: python -m elegant_chart.app
```

- **Data**: an MMA series ID (uses the same token and Excel cache as `get_series_df`) or an
  uploaded `.xlsx` / `.csv` file (pick a sheet for multi-sheet workbooks).
- **Reshape**: an ordered list of steps: filter, group + aggregate, sort, top N, and
  pivot (long → wide). You can add, edit, reorder or delete steps. If a step fails, the
  error shows on that step and the steps after it are skipped. No step is ever skipped
  silently.
- **Style**: Chart / Text / Axes / Colors / … (layout and legend) cover the library's
  parameters. Switching between bar, horizontal bar, line and bump keeps the data,
  the steps and every shared setting.
- **Hand-held by design**: a progress checklist (Data → Chart → Titles → Look → Export)
  names the next step; an MMA fetch shows the series name, frequency and unit; settings
  that take a format list their options *with the result from your data* (date style,
  number style, theme cards drawn as mini charts, series colour swatches); every control
  has plain wording and a short help line. Date styles appear only for real date columns.
- **Preview** is drawn by the real matplotlib renderer at the canonical figsize. Only the
  `savefig` DPI is lower, so the preview and the export are the same image.
- **Export PNG** gives you the image (1080 × 1350 px, 500 DPI); **Data .xlsx** gives you `chart_data.xlsx`.

The app is a thin layer over three library functions, which you can also use directly:

```python
from elegant_chart import ChartSpec, apply_steps, render
from elegant_chart.render import figure_png_bytes
from elegant_chart.spec import StepSpec

spec = ChartSpec()
spec.steps = [
    StepSpec("filter", {"column": "Type", "operator": "=", "value": "International"}),
    StepSpec("group", {"by": ["Airline"], "agg": "sum", "columns": ["Total Passengers"]}),
    StepSpec("sort", {"column": "Total Passengers", "ascending": False}),
    StepSpec("top_n", {"n": 10}),
]
spec.chart.type = "hbar"            # "bar" | "hbar" | "line" | "bump"
spec.chart.x_col = "Airline"
spec.chart.y_cols = ["Total Passengers"]
spec.style.text.title = "Maldives Gateway:\nMost Popular Airlines at VIA"

data = apply_steps(df, spec.steps).df
result = render(spec, data)         # same Figure as calling ElegantChart(...).bar(...) by hand
open("chart.png", "wb").write(figure_png_bytes(result.fig, dpi=500))
result.close()
```

## Project Structure

```
elegant_chart/
├── src/
│   └── elegant_chart/
│       ├── __init__.py
│       ├── base.py           ← ChartBase: shared attribute contract + __init__
│       ├── elegant_chart.py  ← ElegantChart: assembles all mixins
│       ├── axis_mixin.py
│       ├── bar_mixin.py
│       ├── line_mixin.py
│       ├── style_mixin.py
│       ├── figure_mixin.py
│       ├── data_mixin.py     ← validation, x-plan, compact_years, shared helpers
│       ├── get_api_data.py
│       ├── types.py
│       ├── spec.py           ← ChartSpec: one serialisable description of a chart
│       ├── pipeline.py       ← apply_steps(): filter / group / sort / top N / pivot
│       ├── sources.py        ← MMA series + CSV/Excel upload loaders
│       ├── render.py         ← render(spec, df): routes the spec onto ElegantChart
│       └── app/              ← Chart Studio (Streamlit GUI); ux.py = pure preview/checklist helpers
├── tests/
│   ├── test_charts.py
│   ├── test_ux.py            ← Chart Studio preview/checklist helpers
│   └── test_studio_app.py    ← Chart Studio app (Streamlit AppTest)
├── .claude/hooks/            ← Stop hook: reminds to update docs after major src changes
├── .github/
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
└── README.md
```

## Extending with Custom Mixins

```python
from elegant_chart import ElegantChart
from elegant_chart.base import ChartBase

class MyAreaMixin:
    def area(self, x, ys, show=True):
        # self.palette, self._rc, etc. are available via ChartBase
        ...

class MyChart(MyAreaMixin, ElegantChart):
    pass

chart = MyChart(title="Area")
chart.area(x=[1, 2, 3], ys=[1, 4, 2])
```

## Roadmap

- Add export options (PNG, SVG, PDF)
- Add built-in chart themes
- Add annotations API
- Add documentation site

## Contributing

Contributions are welcome. Feel free to open an issue or submit a pull request.

## License

MIT License
