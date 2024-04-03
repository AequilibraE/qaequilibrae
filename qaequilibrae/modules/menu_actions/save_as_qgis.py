import os

from qgis.PyQt import QtWidgets, QtCore, uic
from qgis.core import QgsProject, QgsVectorFileWriter
from qgis.PyQt.QtWidgets import QGridLayout, QPushButton, QLineEdit, QVBoxLayout, QWidget
from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.modules.common_tools import GetOutputFileName

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "../common_tools/forms/ui_empty.ui"))


class SaveAsQGZ(QtWidgets.QDialog, FORM_CLASS):
    finished = QtCore.pyqtSignal(object)

    def __init__(self, qgis_project):
        QtWidgets.QDialog.__init__(self)
        self.setWindowTitle(self.tr("Save as QGIS Project"))

        self.iface = qgis_project.iface
        self.setupUi(self)
        self.qgis_project = qgis_project

        self.qgz_project = QgsProject.instance()
        self.layers = self.qgz_project.mapLayers().values()

        self._run_layout = QGridLayout()

        self.output_path = QLineEdit()
        file_name = self.choose_output()
        self.output_path.setText(file_name)

        self.but_run = QPushButton()
        self.but_run.setText(self.tr("Save!"))
        self.but_run.clicked.connect(self.run)

        self.buttons_frame = QVBoxLayout()
        self.buttons_frame.addWidget(self.output_path)
        self.buttons_frame.addWidget(self.but_run)

        self.buttons_widget = QWidget()
        self.buttons_widget.setLayout(self.buttons_frame)

        self.update_widget = QWidget()
        self.update_frame = QVBoxLayout()
        self.update_widget.setLayout(self.update_frame)
        self.update_widget.setVisible(False)

        self._run_layout.addWidget(self.buttons_widget)
        self._run_layout.addWidget(self.update_widget)

        self.setLayout(self._run_layout)
        self.resize(400, 80)

    def choose_output(self):
        file_name, _ = GetOutputFileName(self, "File Path", ["QGIS Project(*.qgz)"], ".qgz", standard_path())
        return file_name

    def save_project(self):
        self.qgz_project.write(self.output_path.text())
        self.finished.emit("projectSaved")

    def __save_temporary_layers(self, layers):
        output_file_path = os.path.join(self.qgis_project.project.project_base_path, "qgis_layers.sqlite")
        if os.path.isfile(output_file_path):
            os.remove(output_file_path)
        file_exists = False

        for layer in layers:
            if layer.isTemporary():
                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = "SQLite"
                if file_exists:
                    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                options.layerName = layer.name()

                transform_context = QgsProject.instance().transformContext()

                error = QgsVectorFileWriter.writeAsVectorFormatV3(layer, output_file_path, transform_context, options)

                if error[0] == QgsVectorFileWriter.NoError:
                    layer.setDataSource(output_file_path + f"|layername={layer.name()}", layer.name(), "ogr")

                file_exists = True

    def run(self):
        self.__save_temporary_layers(self.layers)
        self.save_project()
        self.exit_procedure()

    def exit_procedure(self):
        self.close()
