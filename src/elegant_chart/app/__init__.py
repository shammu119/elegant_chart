# elegant_chart/app/__init__.py
"""Chart Studio — a local GUI for elegant_chart.

Launch with ``elegant-chart-studio`` or ``python -m elegant_chart.app``.
Requires the ``app`` extra: ``pip install "elegant_chart[app]"``.
"""

from __future__ import annotations

import sys
from pathlib import Path

STUDIO_SCRIPT = Path(__file__).with_name("studio.py")
THEME_FILE = Path(__file__).with_name("theme.toml")


def main(argv: list[str] | None = None) -> int:
    """Run ``streamlit run studio.py`` with any extra CLI args passed through."""
    try:
        from streamlit.web import cli as stcli  # noqa: PLC0415
    except ImportError:
        print(
            'Chart Studio needs Streamlit. Install it with:\n    pip install "elegant_chart[app]"',
            file=sys.stderr,
        )
        return 1
    args = list(sys.argv[1:] if argv is None else argv)
    defaults = {
        "--browser.gatherUsageStats": "false",  # personal, local tool
        "--theme.base": str(THEME_FILE),  # Apple-style light/dark theme
        "--client.toolbarMode": "minimal",
    }
    for flag, value in defaults.items():
        if not any(a.startswith(flag) for a in args):
            args += [flag, value]
    sys.argv = ["streamlit", "run", str(STUDIO_SCRIPT), *args]
    return stcli.main()
