# elegant_chart/_logging.py
"""Library-wide logger.

Follows the standard library convention for libraries: a module-level
logger with a :class:`logging.NullHandler` attached so that, by default,
``elegant_chart`` produces no output. Applications (or interactive scripts
such as ``occupancy_rates.py``) opt in via :func:`enable_logging`.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("elegant_chart")
logger.addHandler(logging.NullHandler())


def enable_logging(level: int = logging.INFO) -> None:
    """Attach a console handler to the ``elegant_chart`` logger.

    Call this once (e.g. at the top of a script) to see render progress —
    series counts, resolved axis limits/ticks, save paths, and data exports.

    Parameters
    ----------
    level:
        Minimum severity to emit. Defaults to :data:`logging.INFO`; pass
        :data:`logging.DEBUG` for detailed axis/geometry diagnostics.
    """
    logger.setLevel(level)

    # Avoid stacking duplicate handlers if called more than once.
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
        )
        logger.addHandler(handler)
