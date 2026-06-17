# Elegant Chart - Architecture & Design Principles

This document serves as a guideline for contributing to the `elegant_chart` framework. The core philosophy is to produce print-quality, aesthetically exceptional charts inspired by professional publications like *The Economist* or *Financial Times*, while maintaining a clean, modular Python codebase.



## 1. Design & Aesthetic Principles

### Typography
We prioritize clean, readable, sans-serif typography:
- **Main font**: `SF Pro`
- **Titles**: `SF Pro Text` (Bold, size 18-20 scaled).
- **Captions & Footers**: `SF Pro Display` (Light, scaled).
- **Scale**: The `font_scale` parameter dynamically scales all text, allowing charts to be easily resized for different mediums (mobile vs print) while maintaining visual proportion.

### Minimalist Axes & Grids
- **Spines**: The top and right spines are strictly removed to reduce "chart junk."
- **Grid Lines**: Grids should be subtle and sit *behind* the data (`zorder=0`). We generally prefer horizontal-only grid lines, drawn at `GRID_LINEWIDTH` (0.4pt, scaled).
- **Baseline**: The x-axis spine (zero line) is solid and visually "grounded" — drawn `0.5pt` heavier than the gridlines (`GRID_LINEWIDTH + 0.5`), so it reads as the anchor of the chart. When the y-range spans zero (`ymin < 0 < ymax`), this spine is repositioned to sit exactly at data `y=0` — so the "0" gridline and the baseline render as a single line, with any data dipping below zero appearing below it.
- **Boundary ticks**: The baseline carries explicit, visible downward tick marks at the absolute start and end of the x-axis range — independent of whatever interior ticks the locator chooses — to sharply anchor the data range. Interior x-ticks point downward (`direction="out"`).
- **Ticks**: Ticks are minimal. Y-axis ticks are often hidden entirely (`length=0`) if value labels are used directly on the data elements.
- **Labels**: Y-axis labels are frequently dropped in standard setups in favor of floating value labels above bars/points.
- **Tick Labels**: y-axis tick labels sit *inside* the plot area, near the axis edge (right edge by default, mirroring `y_axis_side`), positioned just **above** their gridline. This keeps the outer margin free for data, Economist-style.

### Color & Theming
Palettes are highly intentional and bounded by themes:
- **Light Themes**: `consulting_light`, `newsroom_muted`.
- **Dark Themes**: `consulting_dark`, `newsroom_dark`.
- **Gradients**: Certain themes leverage procedural gradients. For example, `newsroom_dark` applies a precise vertical gradient on bars (`#0077CC` to `#64D2FF`) for depth, replacing flat fills.
- **Color roles**: Series colors are assigned via named, positional roles (`primary`, `secondary`, `tertiary`, `quaternary`, `quinary`), bound to `palette[0..n]` by `_apply_base_style` into `self.color_roles`. `bar()`/`line()` resolve each series' color through `StyleMixin._series_color(idx, label)` rather than indexing `palette` directly. An optional `color_map={"Series Label": "secondary"}` (role name or literal hex) on `ElegantChart(...)` pins specific series to specific roles/colors.
- **Legend suppression**: A legend is drawn only when **two or more** series carry labels (`DataMixin._should_show_legend`). A single labeled series relies on the subtitle to name its metric instead.

### Layout & Sizing
- **Canonical output**: Strictly **1080 × 1350 px** at **500 DPI** save output. This corresponds to `figsize=(2.16, 2.70)` inches (default). Never change this output resolution without an explicit design decision.
- **Design reference canvas**: `REFERENCE_FIGSIZE = (3.6, 4.5)` inches. All font and geometry base values are authored at this size. When `figsize=(2.16, 2.70)`, `_figure_scale = 0.6` and `_fs()` automatically scales fonts down proportionally — no manual `font_scale` adjustment is needed.
- **Font base sizes** (effective = base × 0.9 × 0.6 at default figsize): title 18 pt, subtitle 12 pt, axes label 11 pt, tick label 10 pt, caption 9 pt.
- **Subplot margins**: left=0.04, right=0.97, top=0.7116, bottom=0.1266. Horizontal margins are kept tight because y-tick labels live inside the plot; top/bottom hold the title/subtitle/legend stack and the footer. The top/bottom values and the title (1.234), subtitle (1.220), and legend (1.15) axes-fraction offsets are co-tuned to give the title a ~3pt margin from the figure's top edge and ~1.5pt gaps between title/subtitle/legend/plot, so a **two-line title** plus a **2-row legend** (4 series, `ncol=3`) both fit without clipping or overlapping the plot. The legend's `handlelength` (`_px(1.4)`) and `labelspacing` (`0.1`) are kept short/tight to minimize its vertical footprint, freeing headroom for the title. The footer's `footer_line_y` (0.0666) and `caption_y` (0.0546) are absolute figure-fraction constants tuned so the x-tick labels land a tight ~2pt above the footer rule (the caption/logo have ~0pt of spare headroom below them at this position). When the baseline relocates to data `y=0` (see Baseline, above), its tick labels move with it, away from `bottom`; the footer is pulled up to match (`footer_line_y = bottom`, `caption_y = bottom - 0.012`), landing ~3.5pt below the relocated labels instead of the much larger gap an unmoved footer would leave.
- **X-axis padding**: left = an auto-measured pad added below the data minimum, sized to half the rendered width of the first major tick label, so that label can stay centered on its tick (like every interior label) without bleeding past the left edge. Right = the larger of two auto-measured pads added beyond the data maximum — one sized to clear the inside y-tick labels, the other to half the last tick label's rendered width so it too can stay centered — override either via `x_upper_pad` (relative to the data span; contributes to the right side's y-tick-clearance pad only, the label-centering pad still applies on top), or skip all of the above entirely by passing an explicit `xlim`. Y-tick label pad: 0.
- **Edge tick labels & minor ticks**: `align_x_edges` (default `True`) keeps the first *and* last major x-tick labels centered on their ticks, exactly like every interior label — the X-axis padding above is what keeps them from clipping past the plot's edges; `align_x_edges=False` centers every label too but skips that extra padding. `x_minor_ticks` adds N evenly-spaced, unlabeled minor ticks between each pair of major ticks (e.g. `1` ⇒ a single midpoint tick, such as mid-year on a yearly axis).
- **Legend**: When shown, arranged as a 2-3 column horizontal grid (`ncol = min(3, n_series)`), left-aligned, positioned between the subtitle and the top of the plot area. Items wrap to a second row only after columns fill.
- **Alignment**: Titles and subtitles are flush left. Captions sit flush bottom. Logos are strategically placed at the top right or bottom right without interfering with the title layout.

### Smart Data Representation
- **Auto-Sizing**: Bar widths and spacing are auto-calculated based on data density (datetime vs categorical spacing).
- **Compact Formatting**: Numbers are aggressively compacted (e.g., 1000 -> 1K) to preserve chart real estate.
- **Value Labels**: Value labels are printed directly above bars or alongside lines (`zorder=5`) for immediate readability, eliminating the need for users to scan back to the y-axis.
