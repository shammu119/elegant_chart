# Elegant Chart

`elegant_chart` is a lightweight collection of Matplotlib mixins bundled into an `ElegantChart` helper class for quickly producing polished bar and line charts. The package centralizes styling, axis formatting, gradients, and figure layout while keeping a minimal set of dependencies.

## Installation

Install the package from the repository root using an editable install:

```bash
pip install -e .
```

## Usage

```python
from elegant_chart import ElegantChart

chart = ElegantChart(title="Demo")
chart.line(x=["A", "B", "C"], ys=[1, 3, 2])
```

The class exposes `line` and `bar` helpers along with configuration options for themes, logos, and axis formatting. See the mixin modules inside `elegant_chart/` for additional customization options.
