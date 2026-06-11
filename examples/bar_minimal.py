# examples/bar_minimal.py
"""
Minimal bar() example.

Self-contained: copy this whole file and run it as-is.
Uses a small mock pandas DataFrame and only the arguments you actually
need — everything else falls back to sensible defaults.
"""

import pandas as pd

from elegant_chart import ElegantChart

df = pd.DataFrame(
    {
        "quarter": ["Q1", "Q2", "Q3", "Q4"],
        "revenue": [120_000, 145_000, 132_000, 168_000],
    }
)

chart = ElegantChart(title="Quarterly Revenue")
chart.bar(df=df, x_col="quarter", y_cols="revenue")
