# examples/line_minimal.py
"""
Minimal line() example.

Self-contained: copy this whole file and run it as-is.
Uses mock numpy arrays and only the arguments you actually need.
"""

import numpy as np

from elegant_chart import ElegantChart

x = np.arange(2015, 2024)
y = np.array([3.1, -0.8, 5.4, 4.2, 3.7, 1.9, -6.3, 18.9, 13.5])

chart = ElegantChart(title="Annual GDP Growth", ylabel="%")
chart.line(x=x.tolist(), ys=y.tolist(), y_formatter="plain")
