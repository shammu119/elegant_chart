# elegant_chart/_paths.py
"""
Package-relative asset locations.

Bundled fonts and the default logo live under ``elegant_chart/assets/`` so they
are resolved relative to the *installed package*, not the process's current
working directory. This keeps ``ElegantChart()`` working identically regardless
of where a script imports it from.
"""

from __future__ import annotations

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
LOGO_DIR = ASSETS_DIR / "logo"

DEFAULT_LOGO_PATH = LOGO_DIR / "ce_logo.png"

BUNDLED_FONT_FILES = (
    "SF-Pro.ttf",
    "SF-Pro-Display-Light.otf",
    "SF-Pro-Display-Medium.otf",
    "SF-Pro-Text-Bold.otf",
)
