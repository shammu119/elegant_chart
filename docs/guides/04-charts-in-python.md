# 4. Charts in Python

Everything Chart Studio does, you can also do from a Python script. That's
useful when you remake the same chart every month, or need many charts at
once.

There are two ways to do it:

| Way | Best when |
|---|---|
| **A. `ChartSpec`**: describe the chart, then `render()` it | You want what the app gives you: reshape steps and every setting in one place |
| **B. `ElegantChart`**: call `bar()`, `line()` or `bump()` directly | You already have the data in shape and want a short script |

Both produce exactly the same image. In fact, Chart Studio uses way A behind
the scenes.

## Way A: ChartSpec

A `ChartSpec` has four parts, and they match the app's panels:

```
spec.source   where the data came from     (Data panel)
spec.steps    the reshape steps            (Reshape)
spec.chart    type, columns, type options  (Chart tab)
spec.style    .text  .layout  .axes  .colors  .legend   (the other tabs)
```

Here is the top-10 airlines chart from [Getting started](01-getting-started.md):

```python
from elegant_chart import ChartSpec, apply_steps, render, sources
from elegant_chart.render import figure_png_bytes, chart_data_xlsx_bytes
from elegant_chart.spec import StepSpec

# 1. Load the data. This reads CSV dates as dates, like the app does.
raw = sources.read_uploaded(
    open("examples/data/airlines_sample.csv", "rb").read(), "airlines_sample.csv"
)
# (Or use pandas directly: raw = pd.read_excel("my_file.xlsx"))

# 2. Describe the chart.
spec = ChartSpec()
spec.steps = [
    StepSpec("filter", {"column": "Type", "operator": "=", "value": "International"}),
    StepSpec("group",  {"by": ["Airline"], "agg": "sum", "columns": ["Total Passengers"]}),
    StepSpec("sort",   {"column": "Total Passengers", "ascending": False}),
    StepSpec("top_n",  {"n": 10}),
]
spec.chart.type = "hbar"                    # "bar" | "hbar" | "line" | "bump"
spec.chart.x_col = "Airline"
spec.chart.y_cols = ["Total Passengers"]
spec.chart.show_value_labels = True
spec.style.text.title = "Top 10 airlines\nby passengers"   # \n = new line
spec.style.text.subtitle = "International passengers, 2021-23 combined"
spec.style.text.caption = "Source: sample data"

# 3. Reshape, draw, and save.
data = apply_steps(raw, spec.steps).df
chart = render(spec, data)
open("top10.png", "wb").write(figure_png_bytes(chart.fig, dpi=500))   # 1080 × 1350
open("chart_data.xlsx", "wb").write(chart_data_xlsx_bytes(chart.chart))
chart.close()
```

To switch the chart to a line chart, change only one thing:

```python
spec.chart.type = "line"
```

### Steps you can use

| Step | Settings | Example |
|---|---|---|
| `filter` | `column`, `operator` (`=` `≠` `>` `≥` `<` `≤` `in`), `value` | `{"column": "Market", "operator": "in", "value": "China, India"}` |
| `group` | `by` (list), `agg` (`sum` `mean` `count` `min` `max`), `columns` (list) | `{"by": ["Airline"], "agg": "sum", "columns": ["Total Passengers"]}` |
| `sort` | `column`, `ascending` | `{"column": "Arrivals", "ascending": False}` |
| `top_n` | `n` | `{"n": 10}` |
| `pivot` | `index`, `columns`, `values` | `{"index": "Year", "columns": "Market", "values": "Arrivals"}` |

### Checking for errors

`apply_steps` doesn't stop your script when a step fails. It tells you which
step went wrong:

```python
result = apply_steps(raw, spec.steps)
if not result.ok:
    print("Step", result.failed_index + 1, "failed:", result.steps[result.failed_index].error)
```

### Common settings

```python
spec.style.colors.theme = "consulting_light"
spec.style.colors.color_map = {"Emirates": "secondary", "IndiGo": "#64D2FF"}
spec.style.axes.x_date_format = "%b %y"
spec.style.axes.x_tick_step = 1
spec.style.axes.y_formatter = "percent"     # compact | plain | percent | norm_max | custom
spec.style.layout.logo_mode = "none"        # default | none | custom
spec.style.legend.legend_ncol = 2
spec.style.text.annotations = [
    {"x": "2024-03-01", "y": 213842, "text": "Busiest spring yet", "dx": -75, "dy": 12, "arrow": True},
]
```

To see every available setting, look in `src/elegant_chart/spec.py`. Each
field there matches one control in the app.

### Runnable example

[`examples/chart_spec_recipes.py`](../../examples/chart_spec_recipes.py)
builds three of the recipes from the sample data:

```bash
python examples/chart_spec_recipes.py
```

The charts are written to `output/recipes/`.

## Way B: ElegantChart directly

When your data is already in shape, this is the shortest route:

```python
import pandas as pd
from elegant_chart import ElegantChart

df = pd.read_csv("examples/data/tourist_arrivals_sample.csv", parse_dates=["Month"])

chart = ElegantChart(
    title="Tourist arrivals\nclimb year on year",
    subtitle="Monthly tourist arrivals, 2022-24",
    caption="Source: sample data",
    theme="consulting_light",
)
chart.line(
    df=df, x_col="Month", y_cols="Arrivals",
    x_date_format="%b %y",
    show=False, save_path="arrivals.png",   # also writes chart_data.xlsx next to it
)
```

[USAGE.md](../../USAGE.md) lists every option of `bar()`, `line()` and
`bump()`, and the scripts in [`examples/`](../../examples/) show real charts
made this way.

---

← [Back to all guides](README.md)
