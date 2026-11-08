# elegant_chart/app/__init__.py
"""Chart Studio — a local GUI for elegant_chart.

Launch with ``elegant-chart-studio`` or ``python -m elegant_chart.app``.
Requires the ``app`` extra: ``pip install "elegant_chart[app]"``.
"""

from __future__ import annotations

import sys
from pathlib import Path

STUDIO_SCRIPT = Path(__file__).with_name("studio.py")


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
    if not any(a.startswith("--browser.gatherUsageStats") for a in args):
        args += ["--browser.gatherUsageStats", "false"]  # personal, local tool
    sys.argv = ["streamlit", "run", str(STUDIO_SCRIPT), *args]
    return stcli.main()
