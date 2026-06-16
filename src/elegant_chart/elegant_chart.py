# elegant_chart/elegant_chart.py
"""
ElegantChart — the main public class.

MRO (left-to-right): StyleMixin → AxisMixin → FigureMixin → LineMixin → BarMixin → BumpMixin → ChartBase
``__init__`` resolves to ``ChartBase.__init__``, which populates the shared attribute contract
and then calls ``self._apply_base_style()`` (supplied by StyleMixin).
"""

from __future__ import annotations

from .base import ChartBase
from .style_mixin import StyleMixin
from .axis_mixin import AxisMixin
from .figure_mixin import FigureMixin
from .line_mixin import LineMixin
from .bar_mixin import BarMixin
from .bump_mixin import BumpMixin


class ElegantChart(
    StyleMixin,
    AxisMixin,
    FigureMixin,
    LineMixin,
    BarMixin,
    BumpMixin,
    ChartBase,
):
    """
    A flexible charting class built from composable mixins.

    All constructor parameters are defined and documented in
    :class:`~elegant_chart.base.ChartBase`.  Create an instance, then call
    :meth:`bar` or :meth:`line` to render a chart.

    Example
    -------
    ::

        from elegant_chart import ElegantChart

        chart = ElegantChart(title="Revenue", theme="consulting_light")
        chart.bar(
            x=["Q1", "Q2", "Q3", "Q4"],
            ys=[120, 145, 132, 168],
            show=True,
        )
    """
    # __init__ is inherited from ChartBase via MRO — no override needed.
