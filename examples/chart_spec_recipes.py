# examples/chart_spec_recipes.py
"""
Build the Chart Studio guide's recipes in Python, using the sample data in
examples/data/.  Run from the repository root:

    python examples/chart_spec_recipes.py

It writes the PNG files to output/recipes/ and also saves chart_data.xlsx for
the first chart.  See docs/guides/04-charts-in-python.md.
"""

from pathlib import Path

from elegant_chart import ChartSpec, apply_steps, render, sources
from elegant_chart.render import chart_data_xlsx_bytes, figure_png_bytes
from elegant_chart.spec import StepSpec

DATA = Path(__file__).parent / "data"
OUT = Path("output/recipes")


def load(name: str):
    """Read a sample CSV the same way the app does (ISO dates become dates)."""
    path = DATA / name
    return sources.read_uploaded(path.read_bytes(), path.name)


def save(spec: ChartSpec, raw, filename: str, with_data: bool = False) -> None:
    result = apply_steps(raw, spec.steps)
    if not result.ok:
        bad = result.steps[result.failed_index]
        raise SystemExit(f"Step {result.failed_index + 1} failed: {bad.error}")
    chart = render(spec, result.df)
    try:
        (OUT / filename).write_bytes(figure_png_bytes(chart.fig, dpi=500))
        if with_data:
            (OUT / "chart_data.xlsx").write_bytes(chart_data_xlsx_bytes(chart.chart))
    finally:
        chart.close()
    print("saved", OUT / filename)


def top10_airlines() -> None:
    spec = ChartSpec()
    spec.steps = [
        StepSpec("filter", {"column": "Type", "operator": "=", "value": "International"}),
        StepSpec("group", {"by": ["Airline"], "agg": "sum", "columns": ["Total Passengers"]}),
        StepSpec("sort", {"column": "Total Passengers", "ascending": False}),
        StepSpec("top_n", {"n": 10}),
    ]
    spec.chart.type = "hbar"
    spec.chart.x_col = "Airline"
    spec.chart.y_cols = ["Total Passengers"]
    spec.chart.show_value_labels = True
    spec.style.text.title = "Top 10 airlines\nby passengers"
    spec.style.text.subtitle = "International passengers, 2021-23 combined"
    spec.style.text.caption = "Source: sample data"
    save(spec, load("airlines_sample.csv"), "top10_airlines.png", with_data=True)


def monthly_arrivals() -> None:
    spec = ChartSpec()
    spec.chart.type = "line"
    spec.chart.x_col = "Month"
    spec.chart.y_cols = ["Arrivals"]
    spec.style.colors.theme = "consulting_light"
    spec.style.axes.x_date_format = "%b %y"
    spec.style.text.title = "Tourist arrivals\nclimb year on year"
    spec.style.text.subtitle = "Monthly tourist arrivals, 2022-24"
    spec.style.text.caption = "Source: sample data"
    spec.style.text.annotations = [
        {
            "x": "2024-03-01",
            "y": 213842,
            "text": "Busiest spring yet",
            "dx": -75,
            "dy": 12,
            "arrow": True,
        },
    ]
    save(spec, load("tourist_arrivals_sample.csv"), "monthly_arrivals.png")


def market_ranks() -> None:
    spec = ChartSpec()
    spec.steps = [
        StepSpec("pivot", {"index": "Year", "columns": "Market", "values": "Arrivals"}),
    ]
    spec.chart.type = "bump"
    spec.chart.x_col = "Year"
    spec.chart.highlight = ["China", "Russia"]
    spec.chart.label_display = {"United Kingdom": "United\nKingdom"}
    spec.style.text.title = "Who sends the\nmost visitors?"
    spec.style.text.subtitle = "Rank of source markets by arrivals"
    spec.style.text.caption = "Source: sample data"
    save(spec, load("arrivals_by_market_sample.csv"), "market_ranks.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    top10_airlines()
    monthly_arrivals()
    market_ranks()
