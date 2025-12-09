# elegant_chart/figure_mixin.py
from typing import Any, Optional, Tuple
import os
import matplotlib.pyplot as plt


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
            linewidth=0.4,
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
        ax.spines["bottom"].set_linewidth(0.5)

        if self.title and self.subtitle:
            ax.text(
                0.0,
                1.12,
                self.title,
                transform=ax.transAxes,
                fontsize=self._fs(20),
                va="bottom",
                ha="left",
                wrap=True,
                color=self.color_title,
                fontfamily=self.font_title_family,
                fontweight=self.font_title_weight,
            )
            ax.text(
                0.0,
                1.085,
                self.subtitle,
                transform=ax.transAxes,
                fontsize=self._fs(12),
                wrap=True,
                va="top",
                ha="left",
                color=self.color_subtitle,
            )
        elif self.title:
            ax.set_title(
                self.title,
                loc="left",
                pad=0,
                fontfamily=self.font_title_family,
                fontweight=self.font_title_weight,
                fontsize=self._fs(20),
                color=self.color_title,
            )

        if self.xlabel:
            ax.set_xlabel(self.xlabel, color=self.color_axes_label)
        if self.ylabel:
            ax.set_ylabel(self.ylabel, color=self.color_axes_label)

        if has_legend:
            ax.legend(frameon=False, fontsize=self._fs(11))

        plt.subplots_adjust(
            left=0.05,
            right=0.87,
            top=0.82,
            bottom=0.24,
        )

    def _add_footer(self, fig: plt.Figure) -> None:
        has_caption = bool(self.caption)
        has_logo = bool(self.logo_path)

        if not (has_caption or has_logo):
            return

        footer_top = 0.15

        if has_caption:
            fig.text(
                0.05,
                footer_top,
                self.caption,
                ha="left",
                va="top",
                fontsize=self._fs(9),
                color=self.color_caption,
                fontfamily=self.font_caption_family,
                fontweight=self.font_caption_weight,
            )

        if has_logo:
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

            left = 1.0 - logo_width - self.logo_margin_rel
            bottom = footer_top - logo_height

            ax_logo = fig.add_axes([left, bottom, logo_width, logo_height])
            ax_logo.imshow(img)
            ax_logo.axis("off")

    def save_figure(
        self,
        fig: plt.Figure,
        save_path: str,
        dpi: int = 300,
        fmt: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        if fmt is None:
            ext = os.path.splitext(str(save_path))[1].lower().lstrip(".")
            if ext:
                fmt = ext

        if "bbox_inches" in kwargs:
            kwargs.pop("bbox_inches")

        fig.savefig(
            save_path,
            dpi=dpi,
            format=fmt,
            **kwargs,
        )
