from typing import Optional

from qgis.PyQt import QtWidgets, uic


class BaseDialog(QtWidgets.QDialog):
    """
    Generic class for QAequilibraE parent/main dialogs
    (i.e. dialogs called directly from one action in 'menu_actions').

    This class holds the main logic for blocking/allowing scenario changes. The UI setup
    is done with the ``_base_ui_setup`` function, that is always overriden in the class
    configuration. ``BaseDialog`` should only be used for configuring parent dialogs,
    as child dialogs should have an independant blocking/allowing scenario configuration.
    """

    def __init__(
        self,
        ui_file: str,
        qgis_project=None,
        parent: Optional[QtWidgets.QWidget] = None,
        **kwargs,
    ):
        """
        Initializes class.

        Args:
            ui_file (str): Path to .ui file
            qgis_project: QGIS project
            parent (QWidget): parent widget (if exists)
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
            self.finished.connect(self.qgis_project.allow_change_scenario)

        except Exception as e:
            qgis_project.allow_change_scenario()
            raise e

    def _base_ui_setup(self, **kwargs):
        """
        UI initial configuration.
        It should be overridden by child classes for specific customizations.

        Args:
            **kwargs: Additional arguments
        """
        pass
