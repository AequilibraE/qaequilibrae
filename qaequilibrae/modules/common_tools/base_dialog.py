from functools import partial
from typing import Optional

from qgis.PyQt import QtWidgets, uic


class BaseDialog(QtWidgets.QDialog):
    """
    Generic class for QAequilibraE 'main' dialogs
    (i.e. dialogs called directly from one action in 'menu_actions').
    """

    def __init__(
        self,
        ui_file: str,
        qgis_project=None,
        parent: Optional[QtWidgets.QWidget] = None,
        maintains_scenario_block: Optional[str] = None,
        **kwargs,
    ):
        """
        Initializes class.

        Args:
            ui_file (str): Path to .ui file
            qgis_project: QGIS project
            parent (QWidget): parent widget (if exists)
            maintains_scenario_block (str): Class name to mantain the scenario blockage
            **kwargs: Additional arguments
        """
        try:
            super().__init__(parent)
            qgis_project.block_change_scenario()

            self.qgis_project = qgis_project
            self.iface = qgis_project.iface
            self.project = qgis_project.project

            # Load UI
            uic.loadUi(ui_file, self)

            # Custom init
            self._base_ui_setup(**kwargs)

            # Connects finished signal for scenario blockage handling
            self.finished.connect(partial(self._handle_dialog_close, maintains_scenario_block))

        except Exception as e:
            qgis_project.allow_change_scenario()
            raise e

    def _handle_dialog_close(self, maintains_scenario_block):
        open_dialogs = [
            type(w).__name__
            for w in QtWidgets.QApplication.allWidgets()
            if isinstance(w, QtWidgets.QDialog) and w.isVisible()
        ]

        if maintains_scenario_block not in open_dialogs:
            self.qgis_project.allow_change_scenario()
        else:
            self.qgis_project.block_change_scenario()

    def _base_ui_setup(self, **kwargs):
        """
        UI initial configuration.
        It should be overridden by child classes for specific customizations.

        Args:
            **kwargs: Additional arguments
        """
        pass
