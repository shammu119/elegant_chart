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
- **Grid Lines**: Grids should be subtle and sit *behind* the data (`zorder=0`). We generally prefer horizontal-only grid lines.
- **Ticks**: Ticks are minimal. Y-axis ticks are often hidden entirely (`length=0`) if value labels are used directly on the data elements.
- **Labels**: Y-axis labels are frequently dropped in standard setups in favor of floating value labels above bars/points.
- **Tick Labels**: y-axis tick labels sit on the inside the plot with a proper padding so that it does not overlap with bar/line inside the bar. The goal is to use  similiar style used in The Economist charts.

### Color & Theming
Palettes are highly intentional and bounded by themes:
- **Light Themes**: `consulting_light`, `newsroom_muted`.
- **Dark Themes**: `consulting_dark`, `newsroom_dark`.
- **Gradients**: Certain themes leverage procedural gradients. For example, `newsroom_dark` applies a precise vertical gradient on bars (`#0077CC` to `#64D2FF`) for depth, replacing flat fills.

### Layout & Sizing
- **Density**: The standard `figsize` is often tight (e.g., `2.16 x 2.7` inches) with `dpi=500`. This ensures incredibly crisp rendering suited for high-density displays and publications.
- **Alignment**: Titles and subtitles are flush left. Captions sit flush bottom. Logos are strategically placed at the top right or bottom right without interfering with the title layout.

### Smart Data Representation
- **Auto-Sizing**: Bar widths and spacing are auto-calculated based on data density (datetime vs categorical spacing).
- **Compact Formatting**: Numbers are aggressively compacted (e.g., 1000 -> 1K) to preserve chart real estate.
- **Value Labels**: Value labels are printed directly above bars or alongside lines (`zorder=5`) for immediate readability, eliminating the need for users to scan back to the y-axis.
