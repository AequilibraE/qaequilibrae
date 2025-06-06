import os
import ast
import sys
from qgis.PyQt import QtWidgets, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_run_module.ui"))


class RunModuleDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QtWidgets.QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.project = qgis_project.project
        self.setupUi(self)

        self.cob_function.addItems(self.select_func)

        self.but_run.clicked.connect(self.run)
        # self.cob_function.currentIndexChanged.connect(self.select_func)
        # self.select_func()


    def run(self):
        pass

    def select_func(self):
        filepath = os.path.join(self.project.project_base_path, "run/__init__.py")
        with open(filepath, "r", encoding="utf-8") as f:
            file_content = f.read()
        tree = ast.parse(file_content)
        return [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

