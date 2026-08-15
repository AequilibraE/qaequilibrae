import pandas as pd
import pytest

from qaequilibrae.pandas_compat import ensure_regex_capable_strings, pyarrow_lacks_regex_kernels

pc = pytest.importorskip("pyarrow.compute")


@pytest.fixture
def string_storage():
    original = pd.get_option("mode.string_storage")
    yield
    pd.set_option("mode.string_storage", original)


def test_detects_pyarrow_without_regex_kernels(monkeypatch):
    monkeypatch.delattr(pc, "match_substring_regex", raising=False)

    assert pyarrow_lacks_regex_kernels()


def test_leaves_a_healthy_pyarrow_alone(monkeypatch, string_storage):
    # Set the kernels so the test also runs on installs whose PyArrow lacks them
    for kernel in ("match_substring_regex", "replace_substring_regex", "count_substring_regex"):
        monkeypatch.setattr(pc, kernel, getattr(pc, kernel, object()), raising=False)
    pd.set_option("mode.string_storage", "pyarrow")

    assert not pyarrow_lacks_regex_kernels()
    assert not ensure_regex_capable_strings()
    assert pd.get_option("mode.string_storage") == "pyarrow"


def test_regex_string_operations_work_after_the_fallback(monkeypatch, string_storage):
    monkeypatch.delattr(pc, "match_substring_regex", raising=False)

    assert ensure_regex_capable_strings()

    # The expression AequilibraE uses to cull links that do not serve a mode
    net = pd.DataFrame(
        {"modes": pd.Series(["cbtw", "wb", "c"], dtype="str"), "a_node": [1, 2, 3], "b_node": [10, 20, 30]}
    )
    unserved = ~net.modes.str.contains("c")
    net.loc[unserved, "b_node"] = net.loc[unserved, "a_node"]

    assert net.b_node.to_list() == [10, 2, 30]
