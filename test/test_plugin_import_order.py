"""Guards the import order that lets the plugin install its own dependencies.

AequilibraE and the rest of the plugin's dependencies live in ``qaequilibrae/packages``, which only
goes on ``sys.path`` -- and only gets installed -- part way down ``qaequilibrae.py``. Any module
imported above that point that reaches AequilibraE turns a first run without the dependencies into a
``ModuleNotFoundError`` while QGIS is loading the plugin, so the installation is never offered.

Nothing else catches it: CI and every developer machine already have AequilibraE importable, so the
imports resolve there and the ordering only matters on a fresh install (in practice, Windows).
"""

import ast
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).parent.parent
PLUGIN_MODULE = "qaequilibrae.qaequilibrae"


def source_of(module: str):
    """The file backing a dotted module name, and whether it is a package, or None if neither."""
    path = PLUGIN_ROOT.joinpath(*module.split("."))
    if (path / "__init__.py").exists():
        return path / "__init__.py", True
    if path.with_suffix(".py").exists():
        return path.with_suffix(".py"), False
    return None, False


def import_time_nodes(tree: ast.AST):
    """Import statements that run when the module is imported, so everything outside a function."""
    pending = list(ast.iter_child_nodes(tree))
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue  # deferred until the function is called, which is what the lazy imports do
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            yield node
        else:
            pending.extend(ast.iter_child_nodes(node))


def with_parents(name: str):
    """A dotted name preceded by every package Python runs on the way to it."""
    parts = name.split(".")
    return [".".join(parts[: depth + 1]) for depth in range(len(parts))]


def imported_names(node, module: str, is_package: bool):
    """The modules a single import statement can pull in, as dotted names.

    Reaching a submodule executes each package `__init__.py` above it, and several of those
    re-export dialogs that import AequilibraE, so the parents count as imports of their own.
    """
    if isinstance(node, ast.Import):
        names = [alias.name for alias in node.names]
    else:
        if node.level == 0:
            base = node.module
        else:
            package = module if is_package else module.rpartition(".")[0]
            for _ in range(node.level - 1):
                package = package.rpartition(".")[0]
            base = f"{package}.{node.module}" if node.module else package

        # `from x import y` imports x, and y too when y is a submodule rather than an attribute
        names = [base] + [f"{base}.{alias.name}" for alias in node.names]

    return list(dict.fromkeys(parent for name in names for parent in with_parents(name)))


def bootstrap_line(tree: ast.AST) -> int:
    """The line where qaequilibrae.py puts the vendored `packages` folder on sys.path."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or node.attr != "insert":
            continue
        target = ast.unparse(node.value)
        if target in ("sys.path", "path"):
            return node.lineno
    return -1


def imports_reaching_aequilibrae(module: str, chain: list, seen: set, before_line=None):
    """Walks import-time imports from *module*, reporting the ones that land on AequilibraE."""
    if module in seen:
        return
    seen.add(module)

    path, is_package = source_of(module)
    if path is None:  # third party, stdlib, or a name imported from a module rather than a submodule
        return

    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in import_time_nodes(tree):
        if before_line is not None and node.lineno > before_line:
            continue
        for name in imported_names(node, module, is_package):
            if name == "aequilibrae" or name.startswith("aequilibrae."):
                yield chain + [f"{module} (line {node.lineno})"], name
            elif name.startswith("qaequilibrae"):
                yield from imports_reaching_aequilibrae(name, chain + [module], seen, before_line=None)


@pytest.fixture(scope="module")
def plugin_tree():
    path, _ = source_of(PLUGIN_MODULE)
    assert path is not None, f"Cannot find the source of {PLUGIN_MODULE}"
    return ast.parse(path.read_text(encoding="utf-8"))


def test_plugin_puts_its_packages_folder_on_the_path(plugin_tree):
    """qaequilibrae.py still adds its vendored packages folder to sys.path."""
    assert bootstrap_line(plugin_tree) > 0, f"{PLUGIN_MODULE} no longer adds `packages` to sys.path"


def test_nothing_imports_aequilibrae_before_the_packages_bootstrap(plugin_tree):
    """No import above that line reaches AequilibraE, which on a fresh install would kill the plugin."""
    offenders = list(
        imports_reaching_aequilibrae(PLUGIN_MODULE, chain=[], seen=set(), before_line=bootstrap_line(plugin_tree))
    )

    described = "\n".join(f"  {name} <- {' <- '.join(reversed(chain))}" for chain, name in offenders)
    assert not offenders, (
        "These imports run before `packages` is on sys.path, so the plugin dies with a "
        f"ModuleNotFoundError instead of offering to install its dependencies:\n{described}"
    )
