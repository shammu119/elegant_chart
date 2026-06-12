# elegant_chart/figure_mixin.py
import os
from typing import Any, Optional, Tuple

import matplotlib.pyplot as plt

from ._logging import logger
from ._paths import DEFAULT_LOGO_PATH
from .style_mixin import LINESPACING

# Hairline weight for horizontal gridlines, in design points (scaled via _px()).
# The x-axis baseline is drawn at GRID_LINEWIDTH + 0.5 so it reads as visually
# "grounded" against the lighter gridlines above it.
GRID_LINEWIDTH = 0.4


class FigureMixin:
    def _init_figure_and_axes(self) -> Tuple[plt.Figure, plt.Axes]:
        fig, ax = plt.subplots(figsize=self.figsize)
        fig.patch.set_facecolor(self.bg_color)
        ax.set_facecolor(self.bg_color)
        return fig, ax

    def _configure_grid(self, ax: plt.Axes) -> None:
        ax.grid(
            True,
            axis="y",
            linestyle="-",
            linewidth=self._px(GRID_LINEWIDTH),
            color=self.grid_color,
            alpha=0.9,
            zorder=0,
        )
        ax.grid(False, axis="x")

    def _apply_axis_limits(self, ax: plt.Axes, xlim, ylim) -> None:
        if xlim is not None:
            ax.set_xlim(xlim)
        elif self.xlim is not None:
            ax.set_xlim(self.xlim)

        if ylim is not None:
            ax.set_ylim(ylim)
        elif self.ylim is not None:
            ax.set_ylim(self.ylim)

        ymin, ymax = ax.get_ylim()
        if ymin == ymax:
            ymin -= 0.5
            ymax += 0.5
            ax.set_ylim(ymin, ymax)

    def _finalize_axes(
        self, ax: plt.Axes, rotation: float = 0, has_legend: bool = False
    ) -> None:
        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.spines["bottom"].set_visible(True)
        ax.spines["bottom"].set_color(self.color_spine)
        # Baseline is grounded: 0.5pt heavier than the gridlines it anchors.
        ax.spines["bottom"].set_linewidth(self._px(GRID_LINEWIDTH + 0.5))
        # Spine spans exactly the data x-range — not ax.get_xlim(), which may
        # carry extra upper padding (see _apply_x_upper_padding) so the last
        # data point's label can clear the inside y-tick labels.
        _sp_lo, _sp_hi = getattr(self, "_x_data_bounds", None) or ax.get_xlim()
        ax.spines["bottom"].set_bounds(_sp_lo, _sp_hi)

        # When the y-range spans zero, pin the baseline to data y=0 so it doubles
        # as the "0" gridline instead of sitting at ylim[0] with a gap above it.
        # Data dipping below zero then renders below the line.
        ymin, ymax = ax.get_ylim()
        if ymin < 0 < ymax:
            ax.spines["bottom"].set_position(("data", 0))

        if self.show_y_spine and self.y_axis_side in ("left", "right"):
            ax.spines[self.y_axis_side].set_visible(True)
            ax.spines[self.y_axis_side].set_color(self.color_spine)
            ax.spines[self.y_axis_side].set_linewidth(self._px(0.5))

        _title_kwargs = dict(
            transform=ax.transAxes,
            fontsize=self._ts("title"),
            va="bottom",
            ha="left",
            color=self.color_title,
            fontfamily=self.font_title_family,
            fontweight=self.font_title_weight,
            linespacing=LINESPACING,
            clip_on=False,
        )

        if self.title:
            ax.text(0.0, 1.234, self.title, **_title_kwargs)

        if self.subtitle:
            # Single multi-line text block; leading is governed by linespacing
            # rather than a hand-stepped per-line offset.
            ax.text(
                0.0,
                1.220,
                self.subtitle,
                transform=ax.transAxes,
                fontsize=self._ts("subtitle"),
                va="top",
                ha="left",
                color=self.color_subtitle,
                fontfamily=self.font_main_family,
                linespacing=LINESPACING,
                clip_on=False,
            )

        if self.xlabel:
            ax.set_xlabel(self.xlabel, color=self.color_axes_label, fontsize=self._ts("axis_label"))
        if self.ylabel:
            ax.set_ylabel(self.ylabel, color=self.color_axes_label, fontsize=self._ts("axis_label"))

        if has_legend:
            # 2-3 column horizontal grid, left-aligned between the subtitle and
            # the plot top; items wrap to a second row only after filling columns.
            handles, labels = ax.get_legend_handles_labels()
            ncol = max(1, min(3, len(labels)))
            ax.legend(
                handles,
                labels,
                loc="upper left",
                bbox_to_anchor=(0.0, 1.15),
                ncol=ncol,
                frameon=False,
                fontsize=self._ts("legend"),
                handlelength=self._px(1.4),
                handletextpad=self._px(0.4),
                columnspacing=self._px(1.0),
                labelspacing=0.1,
                borderaxespad=0.0,
            )

        # Draw y-tick labels inside or outside the plot area, depending on
        # y_tick_labels_inside; side mirrors y_axis_side. Only the "inside"
        # texts feed _apply_x_upper_padding (they can crowd the data area);
        # both feed _auto_expand_right (either can bleed off the figure).
        inside_ytick_texts: list = []
        outside_ytick_texts: list = []
        if self.y_tick_labels_inside:
            inside_ytick_texts = self._draw_economist_ytick_labels(  # type: ignore[attr-defined]
                ax, secondary=(self.y_axis_side == "right")
            )
        else:
            outside_ytick_texts = self._draw_outside_ytick_labels(  # type: ignore[attr-defined]
                ax, secondary=(self.y_axis_side == "right")
            )

        self._draw_annotations(ax)

        self._auto_expand_bottom(ax)

        # Horizontal-first: y-tick labels now live inside the plot, so the
        # left/right margins can shrink to near-zero dead space. Top/bottom
        # are unchanged — they hold the title/subtitle/legend stack and footer.
        plt.subplots_adjust(
            left=0.04,
            right=0.97,
            top=0.75,
            bottom=0.19,
        )

        self._auto_expand_right(ax, inside_ytick_texts + outside_ytick_texts)

        # Pad the upper x-limit so the rightmost data point / tick label
        # clears the inside y-tick labels living near the right edge.
        self._apply_x_upper_padding(ax, inside_ytick_texts)
        self._apply_year_comb_left_padding(ax)

        # Edge labels: left-align the first major tick, right-align the
        # last, now that xlim/padding and layout have both settled.
        if self._align_x_edges:  # type: ignore[attr-defined]
            self._align_x_edge_labels(ax)  # type: ignore[attr-defined]

        # Anchor the data range with explicit boundary ticks at the exact
        # x start/end, after layout has settled (geometry-dependent).
        self._draw_x_boundary_ticks(ax)  # type: ignore[attr-defined]

    def _draw_annotations(self, ax: plt.Axes) -> None:
        """Draw sparse, muted-grey in-plot annotations declared via `annotations=[...]`.

        Each entry is a dict: {"x", "y", "text", "dx"=0, "dy"=0,
        "ha"="left", "va"="bottom", "arrow"=False}.
        """
        for ann in self.annotations:
            arrowprops = None
            if ann.get("arrow"):
                arrowprops = dict(
                    arrowstyle="-",
                    color=self.color_annotation,
                    linewidth=self._px(0.5),
                )
            ax.annotate(
                ann["text"],
                xy=(ann["x"], ann["y"]),
                xytext=(ann.get("dx", 0), ann.get("dy", 0)),
                textcoords="offset points",
                ha=ann.get("ha", "left"),
                va=ann.get("va", "bottom"),
                fontsize=self._ts("annotation"),
                color=self.color_annotation,
                fontfamily=self.font_main_family,
                arrowprops=arrowprops,
                zorder=5,
            )

    def _auto_expand_bottom(self, ax: plt.Axes) -> None:
        """Re-adjust bottom margin if x-tick labels bleed below the figure boundary."""
        fig = ax.get_figure()
        try:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            tight_bb = fig.get_tightbbox(renderer)
            if tight_bb is None:
                return
            fig_h_px = fig.get_size_inches()[1] * fig.dpi
            tight_bot_frac = tight_bb.y0 / fig_h_px
            if tight_bot_frac < 0.0:
                extra = abs(tight_bot_frac) + 0.01
                plt.subplots_adjust(bottom=min(fig.subplotpars.bottom + extra, 0.45))
        except Exception:
            logger.debug("_auto_expand_bottom geometry step failed", exc_info=True)

    def _auto_expand_right(self, ax: plt.Axes, right_texts: list) -> None:
        """Re-adjust right margin if inside y-tick labels bleed past the figure edge.

        Scoped to ``right_texts`` (the labels floating beyond x=1.0 axes-fraction)
        rather than the whole-figure tight bbox, so an oversized title or other
        wide artist doesn't trigger an unrelated, oversized margin shrink.
        """
        if not right_texts:
            return

        fig = ax.get_figure()
        try:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            fig_w_in = fig.get_size_inches()[0]
            max_x1_in = max(t.get_window_extent(renderer).x1 for t in right_texts) / fig.dpi
            tight_right_frac = max_x1_in / fig_w_in
            if tight_right_frac > 1.0:
                extra = tight_right_frac - 1.0 + 0.01
                plt.subplots_adjust(right=max(fig.subplotpars.right - extra, 0.5))
        except Exception:
            logger.debug("_auto_expand_right geometry step failed", exc_info=True)

    def _apply_x_upper_padding(self, ax: plt.Axes, inside_ytick_texts: list) -> None:
        """Pad the upper x-limit so the last data point clears the inside y-tick labels.

        ``self._x_data_bounds`` (set by ``bar()``/``line()``) holds the *true*
        data range — the spine, boundary ticks, and edge tick labels all
        anchor to it. Here we widen ``ax.get_xlim()`` beyond ``data_hi`` so
        that empty space, not data, sits under the inside y-tick labels on
        the right edge. Skipped entirely when the caller passed an explicit
        ``xlim`` (``self._x_xlim_explicit``) — that range is authoritative.
        """
        if self._x_xlim_explicit:  # type: ignore[attr-defined]
            return

        bounds = self._x_data_bounds  # type: ignore[attr-defined]
        if bounds is None:
            return

        lo, hi = bounds
        span = hi - lo
        if span <= 0:
            return

        rel_pad = self._x_upper_pad  # type: ignore[attr-defined]
        if rel_pad is None:
            rel_pad = self._auto_x_upper_pad(ax, inside_ytick_texts)
            logger.debug("Auto-measured x upper pad: %.4f (relative to data span)", rel_pad)

        if rel_pad > 0:
            ax.set_xlim(lo, hi + rel_pad * span)

    def _auto_x_upper_pad(self, ax: plt.Axes, inside_ytick_texts: list) -> float:
        """Measure how far the inside y-tick labels reach left of the axes' right edge.

        Returns a pad expressed *relative to the data span* (e.g. ``0.05``
        means "add 5% of the data range to the upper xlim"), so it composes
        with ``hi + rel_pad * span`` the same way a manual ``x_upper_pad``
        override does.
        """
        # Inside labels only crowd the x-axis when they sit on the right
        # edge (the default, mirroring y_axis_side="right").
        if self.y_axis_side != "right" or not inside_ytick_texts:
            return 0.0

        fig = ax.get_figure()
        try:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            ax_bbox = ax.get_window_extent(renderer)
            if ax_bbox.width <= 0:
                return 0.0

            # Fraction of the axes width covered by each label, measured
            # leftward from the axes' right edge.
            covered = max(
                (ax_bbox.x1 - t.get_window_extent(renderer).x0) / ax_bbox.width
                for t in inside_ytick_texts
            )
            p = min(covered + 0.015, 0.9)  # small breathing-room gap; cap to avoid blow-up
            return p / (1 - p)
        except Exception:
            logger.debug("_auto_x_upper_pad geometry step failed", exc_info=True)
            return 0.0

    def _apply_year_comb_left_padding(self, ax: plt.Axes) -> None:
        """Shift the lower xlim left so the first (4-digit) year label can
        center under its tick without being clipped by the left edge.

        Only runs when ``_apply_year_tick_comb`` was used for this axis
        (``self._year_tick_comb_active``). Mirrors ``_auto_x_upper_pad``'s
        pixel-to-data-span conversion, but measures the rendered width of
        the first major tick label instead of the inside y-tick labels.
        """
        if not getattr(self, "_year_tick_comb_active", False):
            return

        bounds = self._x_data_bounds  # type: ignore[attr-defined]
        if bounds is None:
            return
        lo, hi = bounds
        span = hi - lo
        if span <= 0:
            return

        fig = ax.get_figure()
        try:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            ax_bbox = ax.get_window_extent(renderer)
            labels = ax.get_xticklabels()
            if ax_bbox.width <= 0 or not labels:
                return

            label_width_px = labels[0].get_window_extent(renderer).width
            p = (label_width_px / 2) / ax_bbox.width
            rel_pad = p / (1 - p)
            ax.set_xlim(lo - rel_pad * span, ax.get_xlim()[1])
        except Exception:
            logger.debug("_apply_year_comb_left_padding geometry step failed", exc_info=True)

    def _add_footer(self, fig: plt.Figure) -> None:
        if not self.show_footer:
            return

        from matplotlib.lines import Line2D

        sp = fig.subplotpars
        footer_line_y = 0.105
        caption_y = 0.093  # footer_line_y - 0.012

        # Baseline rule spanning subplot width
        fig.add_artist(
            Line2D(
                [sp.left, sp.right],
                [footer_line_y, footer_line_y],
                transform=fig.transFigure,
                color=self.color_spine,
                linewidth=self._px(0.5),
                clip_on=False,
            )
        )

        if self.caption:
            fig.text(
                sp.left,
                caption_y,
                self.caption,
                ha="left",
                va="top",
                fontsize=self._ts("caption"),
                color=self.color_caption,
                fontfamily=self.font_caption_family,
                fontweight=self.font_caption_weight,
                linespacing=LINESPACING,
            )

        if self.logo_path is None:
            # Default: bundled package logo, resolved independent of CWD.
            path = str(DEFAULT_LOGO_PATH)
        elif self.logo_path:
            # User-supplied override: resolve relative to the working directory.
            path = os.path.expanduser(self.logo_path)
        else:
            # Falsy (e.g. "") — logo explicitly disabled.
            return

        if not os.path.exists(path):
            return

        try:
            img = plt.imread(path)
        except Exception:
            return

        h_img, w_img = img.shape[:2]
        if h_img <= 0:
            return

        aspect = w_img / h_img
        logo_height = self.logo_height_rel * 0.65

        fig_w, fig_h = fig.get_size_inches()
        fig_aspect = fig_w / fig_h
        logo_width = logo_height * aspect / fig_aspect

        # Right-aligned to subplot right; top flush with baseline rule
        left = sp.right - logo_width
        bottom = footer_line_y - logo_height

        ax_logo = fig.add_axes([left, bottom, logo_width, logo_height])
        ax_logo.imshow(img)
        ax_logo.axis("off")

    def save_figure(
        self,
        fig: plt.Figure,
        save_path: str,
        dpi: int = 500,
        fmt: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        if fmt is None:
            ext = os.path.splitext(str(save_path))[1].lower().lstrip(".")
            if ext:
                fmt = ext

        fig.savefig(
            save_path,
            dpi=dpi,
            format=fmt,
            **kwargs,
        )
