"""Compatibility shims for the pandas/PyArrow stack shipped by the host QGIS install.

Some QGIS distributions (notably OSGeo4W on Windows) ship a PyArrow that was built
without RE2, so every ``*_regex`` compute kernel is missing from ``pyarrow.compute``.
Because pandas 3.0 promoted the Arrow-backed ``str`` dtype to the default for inferred
string columns, regular expression string operations then blow up with::

    AttributeError: module 'pyarrow.compute' has no attribute 'match_substring_regex'

That takes out ``Series.str.contains``/``match``/``fullmatch``/``count`` and
``str.replace(regex=True)``, which both AequilibraE and this plugin rely on - building
the graphs for a traffic assignment being the most visible casualty.

Selecting the ``python`` string storage keeps pandas on its own ``re``-based
implementation, which is what these code paths were written against. String columns in
a model (modes, link types, names) are small, so the cost is negligible; the numeric
work is untouched.
"""

# The kernels pandas reaches for when running a regex over an Arrow-backed string column.
_REGEX_KERNELS = ("match_substring_regex", "replace_substring_regex", "count_substring_regex")


def pyarrow_lacks_regex_kernels() -> bool:
    """Whether the installed PyArrow was built without the regex compute kernels."""
    try:
        import pyarrow.compute as pc
    except ImportError:
        # No PyArrow at all means pandas never takes the Arrow string path.
        return False

    return any(not hasattr(pc, kernel) for kernel in _REGEX_KERNELS)


def ensure_regex_capable_strings() -> bool:
    """Fall back to Python-backed string storage when PyArrow cannot run regexes.

    Only affects arrays built after it runs, so it has to happen before any dataframe
    is created. Returns whether the fallback was applied.
    """
    try:
        import pandas as pd
    except ImportError:
        return False

    if not pyarrow_lacks_regex_kernels():
        return False

    try:
        pd.set_option("mode.string_storage", "python")
    except (AttributeError, KeyError, ValueError):
        # Option renamed or dropped by a future pandas: nothing we can do here, and
        # failing to load the plugin over it would be worse than the original error.
        return False

    return True
