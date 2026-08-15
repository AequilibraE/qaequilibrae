"""Covers the plugin loading on a fresh install, before its dependencies have been installed.

``qaequilibrae.py`` imports AequilibraE-backed modules after offering to install them, so declining
the offer - or having the installation fail - leaves those imports unsatisfiable. The plugin loads
anyway, with stand-ins from ``missing_dependencies`` in place of everything that needs AequilibraE,
because QGIS turns any exception raised while loading a plugin into a Python error report.

CI installs the dependencies before running any of this, so nothing here would ever be exercised by
accident: the state under test is reached by blocking ``aequilibrae`` and re-importing the plugin.
"""

import ast
import importlib.util
import sys
from contextlib import contextmanager
from enum import IntFlag
from pathlib import Path

import pytest

from qaequilibrae.message import FAQ_URL
from qaequilibrae.missing_dependencies import DisabledLinkSplitter, DisabledSnapping
from qaequilibrae.missing_dependencies import disabled_action, temporary_folder

PLUGIN_SOURCE = Path(__file__).parent.parent / "qaequilibrae" / "qaequilibrae.py"
PROBE_MODULE = "qaequilibrae_without_dependencies"


class BlockedImport:
    """Meta path finder that makes a package unimportable, as it is before the install runs."""

    def __init__(self, blocked: str):
        self.blocked = blocked

    def find_spec(self, name, path=None, target=None):
        if name == self.blocked or name.startswith(f"{self.blocked}."):
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return None


class RecordingMessageBox:
    """Stands in for QMessageBox so the install prompt cannot block the test run.

    Answering Cancel is the case being tested: it is what leaves the dependencies missing.

    The buttons live under a nested ``StandardButton`` because that is where PyQt6 keeps them,
    and the plugin spells them that way so it works under both Qt5 and Qt6. IntFlag is what
    makes ``Ok | Cancel`` combine the way the real enum does.
    """

    class StandardButton(IntFlag):
        Ok = 1
        Cancel = 2

    def __init__(self):
        self.shown = []

    def information(self, parent, title, text, *args, **kwargs):
        self.shown.append((title, text))

    def question(self, parent, title, text, *args, **kwargs):
        self.shown.append((title, text))
        return self.StandardButton.Cancel


@contextmanager
def plugin_loaded_on_a_fresh_install(monkeypatch, tmp_path):
    """Imports qaequilibrae.py the way a fresh install would, and hands back the loaded module.

    Two things make an install fresh, and both are reproduced here: no ``packages`` folder beside
    the plugin, so the bootstrap block offers the installation, and no importable AequilibraE, so
    the imports guarded further down cannot be satisfied. The offer is answered with Cancel, which
    is the case that used to leave QGIS showing a traceback.
    """
    from qgis.PyQt import QtWidgets

    # Running from a copy with no `packages` sibling is what makes the install look fresh, and it
    # keeps the result independent of whether this checkout happens to have the folder populated.
    source = tmp_path / "qaequilibrae.py"
    source.write_text(PLUGIN_SOURCE.read_text(encoding="utf-8"), encoding="utf-8")

    message_box = RecordingMessageBox()
    # The plugin does `from qgis.PyQt.QtWidgets import QMessageBox` inside the bootstrap block,
    # so patching the attribute on the module is enough to intercept it.
    monkeypatch.setattr(QtWidgets, "QMessageBox", message_box)

    # A cached qaequilibrae.modules.* would satisfy the imports from sys.modules without ever
    # consulting the finder, so they have to go, and be put back for the rest of the suite.
    cached = {
        name: module
        for name, module in sys.modules.items()
        if name == "aequilibrae" or name.startswith(("aequilibrae.", "qaequilibrae.modules"))
    }
    for name in cached:
        del sys.modules[name]

    finder = BlockedImport("aequilibrae")
    sys.meta_path.insert(0, finder)
    saved_path = list(sys.path)
    try:
        # Loaded under its own name so the copy the rest of the suite imported stays untouched
        spec = importlib.util.spec_from_file_location(PROBE_MODULE, source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.message_box = message_box
        yield module
    finally:
        sys.meta_path.remove(finder)
        sys.path[:] = saved_path
        for name in [n for n in sys.modules if n.startswith(("aequilibrae", "qaequilibrae.modules"))]:
            del sys.modules[name]
        sys.modules.update(cached)
        sys.modules.pop(PROBE_MODULE, None)


@pytest.fixture
def degraded_plugin(monkeypatch, tmp_path):
    with plugin_loaded_on_a_fresh_install(monkeypatch, tmp_path) as module:
        yield module


def test_the_probe_really_does_block_aequilibrae(degraded_plugin):
    """Guards the test itself: if AequilibraE stayed importable everything below would pass hollow."""
    assert degraded_plugin.DEPENDENCY_ERROR is not None, "the plugin imported AequilibraE despite the block"
    assert "aequilibrae" in str(degraded_plugin.DEPENDENCY_ERROR)


def test_plugin_module_imports_without_its_dependencies(degraded_plugin):
    """The whole point: importing the plugin must not raise, or QGIS shows a traceback instead."""
    assert degraded_plugin.AequilibraEMenu is not None


def test_declining_the_install_is_what_left_the_dependencies_missing(degraded_plugin):
    """The offer still has to be made and answered before the degraded load is reached."""
    from qaequilibrae.message import messages

    shown = [text for _, text in degraded_plugin.message_box.shown]
    assert messages().first_message in shown, "the user was never offered the installation"
    assert messages().fourth_message in shown, "declining did not tell the user what to expect"


def test_menu_builds_and_every_action_explains_the_missing_dependencies(degraded_plugin, qgis_iface):
    menu = degraded_plugin.AequilibraEMenu(qgis_iface)

    # The menus are present, which is what messages.fourth_message promises
    assert set(menu.menuActions) >= {"Project", "Traffic assignment", "Mapping", "AequilibraE"}

    entries = [action for name, actions in menu.menuActions.items() if name != "AequilibraE" for action in actions]
    assert entries, "no menu entries were built"

    # Help is the one entry that still works, and it is the route to the instructions
    help_buttons = menu.menuActions["AequilibraE"]
    assert len(help_buttons) == 1


def test_processing_provider_is_not_registered(degraded_plugin, qgis_iface):
    """Registering it makes QGIS import every algorithm, and all of them need AequilibraE."""
    menu = degraded_plugin.AequilibraEMenu(qgis_iface)
    menu.initGui()

    assert menu.provider is None
    menu.unload()  # must stay harmless with nothing registered


def test_logger_falls_back_to_the_standard_library(degraded_plugin, qgis_iface):
    menu = degraded_plugin.AequilibraEMenu(qgis_iface)

    assert menu.logger is not None
    menu.logger.debug("must not raise")


def test_reload_project_does_not_raise_on_a_qgis_project_with_a_model(degraded_plugin, qgis_iface):
    """Wired to a QGIS signal, so it fires on project load whether or not the plugin is degraded."""
    from qgis.core import Qgis, QgsExpressionContextUtils, QgsProject

    menu = degraded_plugin.AequilibraEMenu(qgis_iface)
    saved = QgsProject.instance().customVariables()
    QgsExpressionContextUtils.setProjectVariable(QgsProject.instance(), "aequilibrae_path", "/nonexistent/model")
    try:
        menu.reload_project()
    finally:
        QgsProject.instance().setCustomVariables(saved)

    warnings = qgis_iface.messageBar().messages[Qgis.MessageLevel.Warning]
    assert warnings, "opening a QGIS project with a model said nothing about the missing packages"
    assert FAQ_URL in warnings[0]


def test_disabled_action_points_at_the_installation_instructions(monkeypatch):
    from qaequilibrae import missing_dependencies

    message_box = RecordingMessageBox()
    monkeypatch.setattr(missing_dependencies, "QMessageBox", message_box)

    # Menu entries are bound as partial(action, menu), so it has to take the menu and anything else
    disabled_action(object(), "extra", keyword=True)

    assert len(message_box.shown) == 1
    _, text = message_box.shown[0]
    assert FAQ_URL in text


def test_stand_ins_absorb_what_the_menu_asks_of_them():
    snapping = DisabledSnapping(object())
    snapping.watch(object())
    snapping.layer_removed(object())

    splitter = DisabledLinkSplitter(object())
    splitter.watch(object(), "links")
    splitter.layer_removed(object())

    # The menu builds its toggle from this, and hands the new state back when it is clicked
    assert splitter.enabled() is False
    splitter.set_enabled(True)

    assert Path(temporary_folder()).is_dir()


# --------------------------------------------------------------------------------------------
# Static check: the fallbacks have to keep up with the imports they stand in for.


def guarded_import_block(tree: ast.AST) -> ast.Try:
    """The try/except ImportError wrapping the imports that need AequilibraE."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        caught = [h.type.id for h in node.handlers if isinstance(h.type, ast.Name)]
        if "ImportError" in caught and any(isinstance(stmt, ast.ImportFrom) for stmt in node.body):
            return node
    return None


def names_bound(statements) -> set:
    """Every name a block of statements binds, by import or by assignment."""
    bound = set()
    for statement in statements:
        for node in ast.walk(statement):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                bound.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.Assign):
                bound.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return bound


def test_every_guarded_import_has_a_fallback():
    """Adding a menu action without a stand-in would put the NameError back, at menu build time."""
    block = guarded_import_block(ast.parse(PLUGIN_SOURCE.read_text(encoding="utf-8")))
    assert block is not None, "qaequilibrae.py no longer guards its AequilibraE imports"

    imported = names_bound(block.body) - {"DEPENDENCY_ERROR"}
    fallbacks = names_bound(block.handlers[0].body)

    missing = sorted(imported - fallbacks)
    assert not missing, (
        "These are imported behind the ImportError guard but have no stand-in, so building the "
        f"menu without AequilibraE dies with a NameError: {', '.join(missing)}"
    )
