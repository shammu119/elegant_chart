# chart_types.py
from typing import Callable, Tuple, Union, Optional

FormatterCallable = Callable[[float, int], str]
FormatterSpec = Union[
    str,
    Tuple[str, int],  # e.g. ("norm_max", 2)
    FormatterCallable,
    None,
]


class YFormatter:
    COMPACT = "compact"
    PLAIN = "plain"
    PERCENT = "percent"
    NORM_MAX = "norm_max"
