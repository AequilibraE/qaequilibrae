import os
from importlib.util import spec_from_file_location, module_from_spec

from aequilibrae.context import get_logger
from qgis.PyQt import QtWidgets, uic
from qgis.core import Qgis

from qaequilibrae.modules.common_tools import LogDialog, list_func

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_run_module.ui"))


class RunModuleDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project, logger=None):
        QtWidgets.QDialog.__init__(self)
        self.qgis_project = qgis_project
        self.iface = qgis_project.iface
        self.project = qgis_project.project
        self.setupUi(self)

        self.logger = logger or get_logger()
        self.filepath = os.path.join(self.project.project_base_path, "run/__init__.py")

        self.items = list_func(self.filepath)
        self.cob_function.addItems(self.items)

        self.but_run.clicked.connect(self.run)

    def run(self):
        spec = spec_from_file_location("__init__", self.filepath)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        func_name = self.items[self.cob_function.currentIndex()]
        func = getattr(module, func_name)
        result = func()
        self.logger.info(result)

        self.iface.messageBar().pushMessage(self.tr("Run procedures executed"), "", level=Qgis.Info, duration=5)

        self.exit_procedure()

    def exit_procedure(self):
        self.close()

        dlg2 = LogDialog(self.qgis_project, self)
        dlg2.show()
        dlg2.exec_()
