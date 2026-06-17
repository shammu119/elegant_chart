# elegant_chart/figure_mixin.py
import os
from typing import Any, Dict, Optional, Sequence, Tuple

import matplotlib.pyplot as plt

from ._logging import logger
from ._paths import DEFAULT_LOGO_PATH
from .axis_utils import calc_y_axis
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
        if self.show_y_axis:
            ax.grid(
                True,
                axis="y",
                linestyle="-",
                linewidth=self._px(GRID_LINEWIDTH),
                color=self.grid_color,
                alpha=0.9,
                zorder=0,
            )
        else:
            ax.grid(False, axis="y")
        ax.grid(False, axis="x")

    def _apply_axis_limits(
        self,
        ax: plt.Axes,
        xlim,
        ylim,
        data_y_min: Optional[float] = None,
        data_y_max: Optional[float] = None,
        chart_type: Optional[str] = None,
        has_top_label: bool = False,
    ) -> None:
        if xlim is not None:
            ax.set_xlim(xlim)
        elif self.xlim is not None:
            ax.set_xlim(self.xlim)

        self._calculated_y_ticks: Optional[list] = None
        self._y_tick_interval: Optional[float] = None

        if ylim is not None:
            ax.set_ylim(ylim)
        elif self.ylim is not None:
            ax.set_ylim(self.ylim)
        elif data_y_min is not None and data_y_max is not None and chart_type is not None:
            result = calc_y_axis(data_y_min, data_y_max, chart_type, has_top_label=has_top_label)
            ax.set_ylim(result["y_min"], result["y_max"])
            self._calculated_y_ticks = result["ticks"]
            self._y_tick_interval = result["tick_interval"]

        ymin, ymax = ax.get_ylim()
        if ymin == ymax:
            ymin -= 0.5
            ymax += 0.5
            ax.set_ylim(ymin, ymax)

    def _finalize_axes(self, ax: plt.Axes, rotation: float = 0, has_legend: bool = False) -> None:
        for spine in ax.spines.values():
            spine.set_visible(False)

        ax.spines["bottom"].set_visible(True)
        ax.spines["bottom"].set_color(self.color_spine)
        # Baseline is grounded: 0.5pt heavier than the gridlines it anchors.
        ax.spines["bottom"].set_linewidth(self._px(GRID_LINEWIDTH + 0.5))
        # Spine spans the data x-range — not ax.get_xlim(), which may carry
        # extra upper padding (see _apply_x_upper_padding) so the last data
        # point's label can clear the inside y-tick labels. For bar charts,
        # also widen by _bar_half_width so the baseline spans the full visual
        # extent of the edge bars rather than stopping at their centers.
        _sp_lo, _sp_hi = getattr(self, "_x_data_bounds", None) or ax.get_xlim()
        _half_w = getattr(self, "_bar_half_width", None) or 0.0
        ax.spines["bottom"].set_bounds(_sp_lo - _half_w, _sp_hi + _half_w)

        # When the y-range spans zero, pin the baseline to data y=0 so it doubles
        # as the "0" gridline instead of sitting at ylim[0] with a gap above it.
        # Data dipping below zero then renders below the line.
        ymin, ymax = ax.get_ylim()
        self._baseline_relocated = ymin < 0 < ymax  # type: ignore[attr-defined]
        if self._baseline_relocated:
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
            if self.legend_ncol is not None:
                ncol = max(1, min(self.legend_ncol, len(labels)))
            else:
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
        if self.show_y_axis:
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
            top=0.7116,
            bottom=0.1266,
        )

        self._auto_expand_right(ax, inside_ytick_texts + outside_ytick_texts)

        # Pad the upper x-limit so the rightmost data point / tick label
        # clears the inside y-tick labels living near the right edge.
        self._apply_x_upper_padding(ax, inside_ytick_texts)
        # Further pad each edge, if needed, so the first/last major tick
        # labels can stay centered on their ticks — like every interior
        # label — instead of bleeding past the plot's left/right edges.
        self._apply_first_label_left_padding(ax)
        self._apply_last_label_right_padding(ax)

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

    def _auto_expand_left(self, ax: plt.Axes, extra_reserve: float = 0.0) -> None:
        """Re-adjust the left margin to fit outside y-tick labels (e.g. horizontal
        bar category names), which the default ``left=0.04`` margin assumes away.

        ``extra_reserve`` is an additional figure-fraction width (e.g. for
        per-row logos drawn just outside the labels via ``_add_y_tick_logos``)
        reserved beyond the labels themselves.
        """
        fig = ax.get_figure()
        labels = ax.get_yticklabels()
        if not labels:
            return
        try:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            fig_w_in = fig.get_size_inches()[0]
            min_x0_in = min(t.get_window_extent(renderer).x0 for t in labels) / fig.dpi
            overflow_frac = -min_x0_in / fig_w_in + extra_reserve
            if overflow_frac > 0:
                new_left = fig.subplotpars.left + overflow_frac + 0.01
                plt.subplots_adjust(left=min(new_left, 0.5))
        except Exception:
            logger.debug("_auto_expand_left geometry step failed", exc_info=True)

    def _add_y_tick_logos(
        self,
        ax: plt.Axes,
        base_positions: Any,
        x: Sequence[Any],
        logo_map: Dict[str, str],
        icon_size_pt: float,
        gap_pt: float,
    ) -> None:
        """Draw a small logo image just to the right of each y-tick label
        (between the label and the axis) whose category (from ``x``) has an
        entry in ``logo_map`` (label -> image path).

        Sized off the final (post ``_auto_expand_left``) tick-label positions.
        Callers must reserve room for the icon between the label and the axis
        by adding ``icon_size_pt + gap_pt`` to the y-tick ``pad`` *and* passing
        the same amount as ``extra_reserve`` to ``_auto_expand_left``
        beforehand.
        """
        fig = ax.get_figure()
        try:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            fig_w_px, fig_h_px = fig.get_size_inches() * fig.dpi
            icon_size_px = icon_size_pt * fig.dpi / 72.0
            gap_px = gap_pt * fig.dpi / 72.0

            for pos, label, text in zip(base_positions, x, ax.get_yticklabels()):
                path = logo_map.get(str(label))
                if not path or not os.path.exists(path):
                    continue
                try:
                    img = plt.imread(path)
                except Exception:
                    continue

                bbox = text.get_window_extent(renderer)
                icon_left_px = bbox.x1 + gap_px
                center_y_px = (bbox.y0 + bbox.y1) / 2.0
                icon_bottom_px = center_y_px - icon_size_px / 2.0

                icon_ax = fig.add_axes([
                    icon_left_px / fig_w_px,
                    icon_bottom_px / fig_h_px,
                    icon_size_px / fig_w_px,
                    icon_size_px / fig_h_px,
                ])
                icon_ax.imshow(img)
                icon_ax.axis("off")
        except Exception:
            logger.debug("_add_y_tick_logos geometry step failed", exc_info=True)

    def _apply_x_upper_padding(self, ax: plt.Axes, inside_ytick_texts: list) -> None:
        """Pad the x-limits so the last data point clears the inside y-tick labels
        and, for bar charts, so the edge bars aren't clipped by the axes boundary.

        ``self._x_data_bounds`` (set by ``bar()``/``line()``) holds the *true*
        data range — the spine, boundary ticks, and edge tick labels all
        anchor to it. Here we widen ``ax.get_xlim()`` beyond ``data_hi`` so
        that empty space, not data, sits under the inside y-tick labels on
        the right edge. Skipped entirely when the caller passed an explicit
        ``xlim`` (``self._x_xlim_explicit``) — that range is authoritative.

        ``self._bar_half_width`` (set by ``bar()``) is half the rendered bar
        width: each edge bar's center sits at a data bound, so its outer half
        extends that far past the bound. Without this padding, the edge bars
        get clipped to half their width and appear misaligned under their
        x-tick labels.
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

        upper_pad = rel_pad * span if rel_pad else 0.0
        half_w = getattr(self, "_bar_half_width", None) or 0.0

        new_lo = lo - half_w
        new_hi = hi + max(upper_pad, half_w)
        if new_lo != lo or new_hi != hi:
            ax.set_xlim(new_lo, new_hi)

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

    def _apply_first_label_left_padding(self, ax: plt.Axes) -> None:
        """Shift the lower xlim left so the first major x-tick label can
        center under its tick (like every interior label) without being
        clipped by the left edge.

        Counterpart to ``_apply_last_label_right_padding`` on the right.
        Skipped when edge labels aren't centered at all
        (``self._align_x_edges`` is ``False``) or the caller passed an
        explicit ``xlim`` (authoritative, never auto-adjusted). Only
        extends the lower bound — never shrinks it — so any padding
        ``_apply_x_upper_padding`` already added for a bar's half-width is
        preserved.
        """
        if not self._align_x_edges or self._x_xlim_explicit:  # type: ignore[attr-defined]
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
            needed_lo = lo - rel_pad * span
            current_lo = ax.get_xlim()[0]
            ax.set_xlim(min(current_lo, needed_lo), ax.get_xlim()[1])
        except Exception:
            logger.debug("_apply_first_label_left_padding geometry step failed", exc_info=True)

    def _apply_last_label_right_padding(self, ax: plt.Axes) -> None:
        """Shift the upper xlim right so the last major x-tick label can
        center under its tick (like every interior label) without being
        clipped by the right edge.

        Counterpart to ``_apply_first_label_left_padding`` on the left.
        Runs after ``_apply_x_upper_padding``, whose own padding (clearing
        the inside y-tick labels, or a bar's half-width) is preserved via
        ``max()`` — this only extends the upper bound further when the
        centered label needs more room than that padding already gives it.
        Skipped under the same conditions as the left counterpart.
        """
        if not self._align_x_edges or self._x_xlim_explicit:  # type: ignore[attr-defined]
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

            label_width_px = labels[-1].get_window_extent(renderer).width
            p = (label_width_px / 2) / ax_bbox.width
            rel_pad = p / (1 - p)
            needed_hi = hi + rel_pad * span
            current_hi = ax.get_xlim()[1]
            ax.set_xlim(ax.get_xlim()[0], max(current_hi, needed_hi))
        except Exception:
            logger.debug("_apply_last_label_right_padding geometry step failed", exc_info=True)

    def _add_footer(self, fig: plt.Figure) -> None:
        if not self.show_footer:
            return

        from matplotlib.lines import Line2D

        sp = fig.subplotpars
        footer_line_y = 0.0666
        caption_y = 0.0546  # footer_line_y - 0.012

        if self.caption:
            caption_text = fig.text(
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

            # A tall (multi-line) caption can extend below the figure's
            # bottom edge at the default caption_y, clipping its last
            # line(s). Measure its rendered height and, if it overflows,
            # shift the footer rule/caption up — and shrink the axes by the
            # same amount, so the gap to the x-tick labels is preserved —
            # just enough to bring it back on-canvas.
            try:
                fig.canvas.draw()
                renderer = fig.canvas.get_renderer()
                bbox = caption_text.get_window_extent(renderer)
                fig_h_px = fig.get_size_inches()[1] * fig.dpi
                pad_px = self._px(20.0)
                overflow = (pad_px - bbox.y0) / fig_h_px
                if overflow > 0:
                    footer_line_y += overflow
                    caption_y += overflow
                    caption_text.set_y(caption_y)
                    plt.subplots_adjust(bottom=sp.bottom + overflow)
            except Exception:
                logger.debug("_add_footer caption overflow check failed", exc_info=True)

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
