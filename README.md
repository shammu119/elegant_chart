# elegant_chart

A lightweight and flexible charting toolkit built in Python. The project uses a modular mixin
architecture that allows you to create customisable charts with clean and extensible code.

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

df = get_series_df(2307)
df.to_excel("data.xlsx", index=False)
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
│       └── types.py
├── tests/
│   └── test_charts.py
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
