# elegant_chart/figure_mixin.py
from typing import Any, Optional, Tuple
import os
import matplotlib.pyplot as plt

from .style_mixin import LINESPACING


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
            linewidth=self._px(0.4),
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
        ax.spines["bottom"].set_linewidth(self._px(0.5))
        # Spine spans exactly the data x-range (xlim is set to data bounds in bar/line mixin).
        _sp_lo, _sp_hi = ax.get_xlim()
        ax.spines["bottom"].set_bounds(_sp_lo, _sp_hi)

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
            ax.text(0.0, 1.24, self.title, **_title_kwargs)

        if self.subtitle:
            # Single multi-line text block; leading is governed by linespacing
            # rather than a hand-stepped per-line offset.
            ax.text(
                0.0,
                1.20,
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
            ax.legend(
                loc="upper left",
                bbox_to_anchor=(-0.01, 1.09),
                frameon=False,
                fontsize=self._ts("legend"),
                handletextpad=self._px(0.4),
                labelspacing=0.15,
                borderaxespad=0.0,
            )

        # Draw inside tick labels only when requested; side mirrors y_axis_side.
        if self.y_tick_labels_inside:
            self._draw_economist_ytick_labels(  # type: ignore[attr-defined]
                ax, secondary=(self.y_axis_side == "right")
            )

        self._draw_annotations(ax)

        self._auto_expand_bottom(ax)

        plt.subplots_adjust(
            left=0.08,
            right=0.92,
            top=0.76,
            bottom=0.24,
        )

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
            pass

    def _add_footer(self, fig: plt.Figure) -> None:
        if not self.show_footer:
            return

        from matplotlib.lines import Line2D

        sp = fig.subplotpars
        footer_line_y = 0.155
        caption_y = 0.143  # footer_line_y - 0.012

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

        if self.logo_path:
            path = os.path.expanduser(self.logo_path)
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
