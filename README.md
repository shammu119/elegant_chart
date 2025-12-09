# elegant_chart

A lightweight and flexible charting toolkit built in Python. The project uses a modular mixin architecture that allows you to create customizable charts with clean and extensible code.

## Features

* Modular system using mixins (axis, bar, line, gradient, style, figure, data)
* Easy to extend with new components
* Simple API for generating charts
* Optional helpers for retrieving data from APIs
* Strong typing for predictable and maintainable behavior

## Installation

### Install directly from GitHub

```bash
pip install git+https://github.com/shammu119/elegant_chart.git
```

### Editable install (recommended during development)

```bash
git clone https://github.com/shammu119/elegant_chart.git
cd elegant_chart
pip install -e .
```

## Quick Start

```python
from elegant_chart import ElegantChart

data = [10, 20, 30, 40]
chart = ElegantChart(data)
chart.show()
```

If your mixins are used to create chart variations:

```python
from elegant_chart.elegant_chart import ElegantChart
from elegant_chart.line_mixin import LineMixin

class MyLineChart(LineMixin, ElegantChart):
    pass

chart = MyLineChart([1, 3, 2, 5])
chart.show()
```

## Project Structure

```
elegant_chart/
│
├── elegant_chart/
│   ├── elegant_chart.py
│   ├── axis_mixin.py
│   ├── bar_mixin.py
│   ├── line_mixin.py
│   ├── gradient_mixin.py
│   ├── style_mixin.py
│   ├── figure_mixin.py
│   ├── data_mixin.py
│   ├── get_api_data.py
│   ├── types.py
│   └── __init__.py
│
├── pyproject.toml
├── README.md
└── .gitignore
```

## Roadmap

* Add built-in chart themes
* Add export options (PNG, SVG, PDF)
* Add animations and transitions
* Add interactive/HTML rendering support
* Add documentation site

## Contributing

Contributions are welcome. Feel free to open an issue or submit a pull request.

## License

MIT License
