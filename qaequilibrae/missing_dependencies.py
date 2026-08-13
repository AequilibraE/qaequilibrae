"""Stand-ins for the parts of the plugin that cannot be imported without AequilibraE.

``qaequilibrae.py`` falls back to these when the packages vendored into ``packages`` are missing,
which is the state of a fresh install until the user accepts the offer to install them - and stays
the state if the user declines, or if the installation fails.

Loading in this degraded state is what ``messages.fourth_message`` promises ("the plugin will be
mostly non-functional"), and it is also the only way to keep the traceback off the screen: QGIS
routes every exception raised while loading a plugin through ``qgis.utils.showException``, so
failing hard here would replace the plugin with a Python error report no matter how good the
message attached to it is. Loading with the menus in place instead means a user who declined the
installation gets a readable explanation at the moment they try to use something.

Nothing here may import AequilibraE, pandas or anything else out of ``packages``, since the whole
point is to be importable when those are absent.
"""

from tempfile import gettempdir

from qgis.PyQt.QtWidgets import QMessageBox

from qaequilibrae.message import messages


def disabled_action(*args, **kwargs):
    """Stands in for every menu action while the dependencies are missing.

    Menu entries are bound as ``partial(action, menu)`` and the actions themselves take varying
    arguments, so this accepts and ignores whatever the real action would have been given.
    """
    msg = messages()
    QMessageBox.information(None, msg.missing_dependencies_box_name, msg.missing_dependencies_message)


def temporary_folder() -> str:
    """Stands in for ``last_folder``, which reaches AequilibraE for its logger."""
    return gettempdir()


class DisabledSnapping:
    """Stands in for ``EditSnapping``, which lives behind the ``common_tools`` imports.

    The menu hands it every layer it tracks, and in this state there is never an AequilibraE
    project to open, so there are no layers to configure snapping for.
    """

    def __init__(self, qgis_project):
        self.qgis_project = qgis_project

    def watch(self, layer):
        pass

    def layer_removed(self, layer):
        pass


class DisabledLinkSplitter(DisabledSnapping):
    """Stands in for ``LinkSplitter``, which lives behind the same imports.

    The menu still builds its toggle, so the setting has to be readable and writable even though
    there is no links layer here for it to act on.
    """

    def watch(self, layer, layer_name):
        pass

    @staticmethod
    def enabled() -> bool:
        return False

    @staticmethod
    def set_enabled(enabled: bool):
        pass
