# elegant_chart/bump_mixin.py
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rc_context

from ._logging import logger
from .data_mixin import DataMixin
from .figure_mixin import GRID_LINEWIDTH
from .style_mixin import LINESPACING

_GHOST_COLOR = "#BBBBBB"
_GHOST_ALPHA = 0.6
_GHOST_LW_PT = 1.0
_HERO_LW_PT = 2.5
_HERO_DOT_PT = 10.0  # markersize = diameter in points


class BumpMixin(DataMixin):
    """Adds a bump() (ranking-flow) chart to ElegantChart.

    Hero series are drawn in bold colour; all others are rendered as thin,
    translucent grey lines with no dots — the classic FT/Bloomberg ghost
    pattern for dense multi-series ranking charts.
    """

    def bump(
        self,
        x: Sequence[Any],
        ys: Dict[str, Sequence[Optional[float]]],
        ascending: bool = False,
        pre_ranked: bool = False,
        # ── hero / ghost styling ──────────────────────────────────────────
        highlight: Optional[List[str]] = None,
        highlight_colors: Optional[Dict[str, str]] = None,
        hero_linewidth: Optional[float] = None,
        other_linewidth: Optional[float] = None,
        other_color: str = _GHOST_COLOR,
        other_alpha: float = _GHOST_ALPHA,
        # ── labels & logos ────────────────────────────────────────────────
        show_labels: bool = True,
        label_logos: Optional[Dict[str, str]] = None,
        label_display: Optional[Dict[str, str]] = None,
        # ── output ───────────────────────────────────────────────────────
        show: bool = True,
        save_path: Optional[str] = None,
        save_dpi: int = 500,
        save_format: Optional[str] = None,
        export_xlsx: bool = True,
        export_xlsx_path: Optional[str] = None,
        **save_kwargs: Any,
    ) -> Tuple[plt.Figure, plt.Axes]:
        """Create a bump (ranking-flow) chart.

        Parameters
        ----------
        x:
            Ordered period labels, e.g. ``[2020, 2021, 2022, 2023]``.
        ys:
            ``{series_label: [value_at_period_0, …]}``. Use ``None`` or
            ``float("nan")`` for periods where a series is absent.
        ascending:
            ``True`` → smallest value = rank 1. Default ``False`` (largest = rank 1).
        pre_ranked:
            ``True`` → *ys* values are already rank integers; skip ranking.
        highlight:
            Names of "hero" series. Heroes get a thick coloured line and a
            filled dot. Unlisted series become thin grey ghosts with no dot.
            Pass ``None`` to treat every series as a hero.
        highlight_colors:
            ``{name: hex}`` colour overrides for hero series. Unlisted heroes
            fall back to the theme palette via ``_series_color``.
        hero_linewidth / other_linewidth:
            Stroke widths (pts) for hero / ghost lines. Defaults: 2.5 / 1.0.
        other_color / other_alpha:
            Fill colour and opacity for ghost lines. Defaults: ``#BBBBBB`` / 0.6.
        show_labels:
            Draw series name labels at the terminal data point of each series.
            Airlines that survive to the final period are labelled in the right
            margin; those that exit earlier are labelled inline at their last
            valid point (still anchored to the right of the terminal dot).
        label_logos:
            ``{name: image_path}`` logo images rendered to the left of each
            label (between the terminal dot and the label text). Paths are
            relative to the process working directory.
        label_display:
            ``{series_key: display_text}`` overrides for the visible label text.
            Supports newlines (``"\\n"``) for wrapping long names. Series keys
            not listed here fall back to their original name.
        show, save_path, save_dpi, save_format, export_xlsx, export_xlsx_path:
            Standard output parameters (same semantics as ``bar()`` / ``line()``).
        """
        if not ys:
            raise ValueError("bump() requires at least one series in 'ys'.")

        series_data: list[tuple[str, list]] = list(ys.items())
        n_series = len(series_data)
        n_periods = len(x)
        x_positions = np.arange(n_periods, dtype=float)
        hero_set: set[str] = (
            set(highlight) if highlight is not None else {lbl for lbl, _ in series_data}
        )
        hcolors: Dict[str, str] = highlight_colors or {}

        # ── value matrix → rank matrix ─────────────────────────────────────
        values_matrix = np.full((n_series, n_periods), np.nan)
        for i, (_, vals) in enumerate(series_data):
            for j, v in enumerate(vals):
                if v is not None and not (isinstance(v, float) and np.isnan(v)):
                    values_matrix[i, j] = float(v)

        if pre_ranked:
            ranks_matrix = values_matrix.copy()
        else:
            ranks_matrix = np.full_like(values_matrix, np.nan)
            for j in range(n_periods):
                col = values_matrix[:, j]
                valid_mask = ~np.isnan(col)
                if not valid_mask.any():
                    continue
                order = np.argsort(col[valid_mask]) if ascending else np.argsort(-col[valid_mask])
                valid_indices = np.where(valid_mask)[0]
                for rank, arr_idx in enumerate(order):
                    ranks_matrix[valid_indices[arr_idx], j] = rank + 1

        n_ranks = int(np.nanmax(ranks_matrix)) if not np.all(np.isnan(ranks_matrix)) else n_series

        # cache for export_data
        self._last_x = list(x)  # type: ignore[attr-defined]
        self._last_series_list = [(lbl, list(vals)) for lbl, vals in series_data]  # type: ignore[attr-defined]

        eff_hero_lw = hero_linewidth if hero_linewidth is not None else self._px(_HERO_LW_PT)  # type: ignore[attr-defined]
        eff_other_lw = other_linewidth if other_linewidth is not None else self._px(_GHOST_LW_PT)  # type: ignore[attr-defined]
        dot_ms = self._px(_HERO_DOT_PT)  # type: ignore[attr-defined]

        # right-margin label space (in data units) for series surviving to final period
        label_x_units = 1.5 if show_labels else 0.0
        x_lo = -0.5
        x_hi = n_periods - 1 + 0.5 + label_x_units

        with rc_context(self._rc):  # type: ignore[attr-defined]
            fig, ax = self._init_figure_and_axes()  # type: ignore[attr-defined]
            ax.grid(False)

            # ── rank reference lines (span data area only) ─────────────────
            for r in range(1, n_ranks + 1):
                ax.plot(
                    [-0.35, n_periods - 1 + 0.35],
                    [r, r],
                    color=self.grid_color,
                    linewidth=self._px(GRID_LINEWIDTH),  # type: ignore[attr-defined]
                    alpha=0.9,
                    zorder=0,
                )

            # ── draw series ────────────────────────────────────────────────
            label_artists: list[tuple[plt.Text, str]] = []  # (text_obj, logo_path)

            # Draw ghost lines first so heroes render on top
            for idx, (lbl, _) in enumerate(series_data):
                if lbl in hero_set:
                    continue
                ranks = ranks_matrix[idx]
                valid = ~np.isnan(ranks)
                xv, yv = x_positions[valid], ranks[valid]
                if len(xv) > 1:
                    ax.plot(
                        xv,
                        yv,
                        color=other_color,
                        linewidth=eff_other_lw,
                        alpha=other_alpha,
                        solid_capstyle="butt",
                        solid_joinstyle="miter",
                        zorder=1,
                    )

            for idx, (lbl, _) in enumerate(series_data):
                is_hero = lbl in hero_set
                ranks = ranks_matrix[idx]
                valid = ~np.isnan(ranks)
                if not valid.any():
                    continue
                xv, yv = x_positions[valid], ranks[valid]

                if is_hero:
                    color = hcolors.get(lbl) or self._series_color(idx, lbl)  # type: ignore[attr-defined]
                    lw, alpha = eff_hero_lw, 1.0
                    zorder_line, zorder_dot = 3, 5
                else:
                    continue  # already drawn above

                if len(xv) > 1:
                    ax.plot(
                        xv,
                        yv,
                        color=color,
                        linewidth=lw,
                        alpha=alpha,
                        solid_capstyle="butt",
                        solid_joinstyle="miter",
                        zorder=zorder_line,
                    )

                # Hero: filled dot at every valid position
                for xp, yp in zip(xv.tolist(), yv.tolist()):
                    ax.plot(
                        xp,
                        yp,
                        "o",
                        color=color,
                        alpha=alpha,
                        markersize=dot_ms,
                        zorder=zorder_dot,
                        markeredgewidth=0,
                    )

            # ── labels ────────────────────────────────────────────────────
            if show_labels:
                last_period_idx = n_periods - 1
                for idx, (lbl, _) in enumerate(series_data):
                    ranks = ranks_matrix[idx]
                    valid = ~np.isnan(ranks)
                    if not valid.any():
                        continue
                    is_hero = lbl in hero_set
                    color = (
                        (hcolors.get(lbl) or self._series_color(idx, lbl))  # type: ignore[attr-defined]
                        if is_hero
                        else other_color
                    )
                    last_valid_idx = int(np.where(valid)[0][-1])
                    lx = x_positions[last_valid_idx]
                    ly = ranks[last_valid_idx]

                    # Extra offset accommodates the logo that sits to the left of the text.
                    x_label = lx + 1.25

                    display_text = (label_display or {}).get(lbl, lbl) or ""
                    font_size = self._ts("tick_label") * 0.88  # type: ignore[attr-defined]
                    txt = ax.text(
                        x_label,
                        ly,
                        display_text,
                        ha="left",
                        va="center",
                        fontsize=font_size,
                        color=color,
                        alpha=1.0 if is_hero else other_alpha,
                        clip_on=False,
                        zorder=6,
                    )
                    logo_path = (label_logos or {}).get(lbl, "")
                    if logo_path:
                        label_artists.append((txt, logo_path))

            # ── left rank axis ─────────────────────────────────────────────
            ax.set_ylim(n_ranks + 0.5, 0.5)  # rank 1 at top
            ax.yaxis.tick_left()
            ax.set_yticks(list(range(1, n_ranks + 1)))
            ax.set_yticklabels(
                [str(i) for i in range(1, n_ranks + 1)],
                fontsize=self._ts("tick_label") * 0.78,  # type: ignore[attr-defined]
                color=self.color_subtitle,  # type: ignore[attr-defined]
            )
            ax.tick_params(axis="y", length=0, pad=self._px(2))  # type: ignore[attr-defined]

            # ── x axis ────────────────────────────────────────────────────
            ax.set_xlim(x_lo, x_hi)
            ax.set_xticks(x_positions)
            ax.set_xticklabels(
                [str(xi) for xi in x],
                fontsize=self._ts("tick_label"),  # type: ignore[attr-defined]
                color=self.color_tick,  # type: ignore[attr-defined]
            )
            ax.tick_params(axis="x", length=0, pad=self._px(5))  # type: ignore[attr-defined]

            # ── spines ────────────────────────────────────────────────────
            for spine in ax.spines.values():
                spine.set_visible(False)

            # ── title / subtitle ──────────────────────────────────────────
            axes_height = 0.7116 - 0.1266
            if self.title:  # type: ignore[attr-defined]
                fig.text(
                    0.04,
                    0.1266 + 1.234 * axes_height,
                    self.title,  # type: ignore[attr-defined]
                    fontsize=self._ts("title"),
                    va="bottom",
                    ha="left",  # type: ignore[attr-defined]
                    color=self.color_title,  # type: ignore[attr-defined]
                    fontfamily=self.font_title_family,  # type: ignore[attr-defined]
                    fontweight=self.font_title_weight,  # type: ignore[attr-defined]
                    linespacing=LINESPACING,
                    clip_on=False,
                )
            if self.subtitle:  # type: ignore[attr-defined]
                fig.text(
                    0.04,
                    0.1266 + 1.220 * axes_height,
                    self.subtitle,  # type: ignore[attr-defined]
                    fontsize=self._ts("subtitle"),
                    va="top",
                    ha="left",  # type: ignore[attr-defined]
                    color=self.color_subtitle,  # type: ignore[attr-defined]
                    fontfamily=self.font_main_family,  # type: ignore[attr-defined]
                    linespacing=LINESPACING,
                    clip_on=False,
                )

            plt.subplots_adjust(left=0.08, right=0.97, top=0.7116, bottom=0.1266)
            self._add_footer(fig)  # type: ignore[attr-defined]

            # ── logos: placed after canvas draw so bboxes are available ───
            if label_artists:
                self._place_bump_logos(fig, label_artists)

            logger.debug(  # type: ignore[attr-defined]
                "Bump chart: %d series × %d periods, %d ranks, %d heroes",
                n_series,
                n_periods,
                n_ranks,
                len(hero_set),
            )

            if save_path is not None:
                self.save_figure(fig, save_path, dpi=save_dpi, fmt=save_format, **save_kwargs)  # type: ignore[attr-defined]
                logger.info("Saved chart -> %s", save_path)  # type: ignore[attr-defined]
                if export_xlsx:
                    target = export_xlsx_path or os.path.join(
                        os.path.dirname(str(save_path)) or ".", "chart_data.xlsx"
                    )
                    try:
                        self.export_data(target)  # type: ignore[attr-defined]
                        logger.info("Exported chart data -> %s", target)  # type: ignore[attr-defined]
                    except ImportError:
                        logger.warning(  # type: ignore[attr-defined]
                            "Skipped xlsx export: openpyxl is not installed."
                        )

            if show:
                plt.show()

            return fig, ax

    # ── logo helper ────────────────────────────────────────────────────────────

    def _place_bump_logos(
        self,
        fig: plt.Figure,
        label_artists: list[tuple[plt.Text, str]],
    ) -> None:
        """Render logo images to the LEFT of each label text artist.

        The logo sits between the terminal dot and the label text. Mirrors the
        geometry approach in ``FigureMixin._add_y_tick_logos``: draw the canvas
        to obtain pixel-accurate bounding boxes, then add each logo as a tiny
        figure-coordinates sub-axes.
        """
        try:
            fig.canvas.draw()
            renderer = fig.canvas.get_renderer()
            fig_w_px, fig_h_px = fig.get_size_inches() * fig.dpi
            icon_pt = self._ts("tick_label") * 4.3  # type: ignore[attr-defined]
            icon_px = icon_pt * fig.dpi / 72.0
            gap_px = self._px(3) * fig.dpi / 72.0  # type: ignore[attr-defined]

            for txt, logo_path in label_artists:
                if not logo_path or not os.path.exists(logo_path):
                    continue
                try:
                    img = plt.imread(logo_path)
                except Exception:
                    continue

                bbox = txt.get_window_extent(renderer)
                # Place logo to the LEFT of the text: right edge of logo at text left edge minus gap
                icon_left_px = bbox.x0 - gap_px - icon_px
                center_y_px = (bbox.y0 + bbox.y1) / 2.0
                icon_bottom_px = center_y_px - icon_px / 2.0

                icon_ax = fig.add_axes(
                    [
                        icon_left_px / fig_w_px,
                        icon_bottom_px / fig_h_px,
                        icon_px / fig_w_px,
                        icon_px / fig_h_px,
                    ]
                )
                icon_ax.imshow(img)
                icon_ax.axis("off")
        except Exception:
            logger.debug("_place_bump_logos geometry step failed", exc_info=True)  # type: ignore[attr-defined]
