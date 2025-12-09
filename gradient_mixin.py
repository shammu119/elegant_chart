# elegant_chart/gradient_mixin.py
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.collections import LineCollection


class GradientMixin:
    def _make_vertical_gradient(
        self, ax, x0, y0, width, height, top_color, bottom_color, z=1
    ):
        grad = np.linspace(0, 1, 256).reshape(-1, 1)
        cmap = mcolors.LinearSegmentedColormap.from_list(
            "bargrad", [bottom_color, top_color]
        )
        ax.imshow(
            grad,
            extent=[x0, x0 + width, y0, y0 + height],
            origin="lower",
            aspect="auto",
            cmap=cmap,
            zorder=z,
        )

    def _interpolate_line(self, x, y, resolution=800):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        if x.size < 2:
            return x, y

        x_new = np.linspace(x.min(), x.max(), resolution)
        y_new = np.interp(x_new, x, y)
        return x_new, y_new

    def _plot_gradient_line(self, ax, x, y, top_color, bottom_color, linewidth):
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        x_s, y_s = self._interpolate_line(x, y, resolution=800)

        points = np.array([x_s, y_s]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)

        dx = np.diff(x_s)
        dy = np.diff(y_s)
        ds = np.hypot(dx, dy)
        s = np.concatenate([[0.0], np.cumsum(ds)])

        if s[-1] > 0:
            s_norm = s[:-1] / s[-1]
        else:
            s_norm = np.zeros_like(s[:-1])

        cmap = mcolors.LinearSegmentedColormap.from_list(
            "linegrad", [bottom_color, top_color]
        )

        lc = LineCollection(
            segments,
            cmap=cmap,
            norm=plt.Normalize(0.0, 1.0),
        )
        lc.set_array(s_norm)
        lc.set_linewidth(linewidth)
        lc.set_capstyle("round")
        lc.set_joinstyle("round")

        ax.add_collection(lc)
        ax.update_datalim(np.column_stack([x_s, y_s]))
        ax.autoscale_view()
