import os

from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsProject, QgsVectorFileWriter
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import QGridLayout, QPushButton, QLineEdit, QVBoxLayout, QWidget
from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.modules.common_tools import GetOutputFileName

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "../common_tools/forms/ui_empty.ui"))


class SaveAsQGZ(QtWidgets.QDialog, FORM_CLASS):
    finished = pyqtSignal(object)

    def __init__(self, qgis_project):
        QtWidgets.QDialog.__init__(self)    
        self.setWindowTitle(self.tr("Save as QGIS Project"))

        self.iface = qgis_project.iface
        self.setupUi(self)
        self.qgis_project = qgis_project

        self._run_layout = QGridLayout()

        self.output_path = QLineEdit()
        self.choose_output()

        self.but_run = QPushButton()
        self.but_run.setText(self.tr("Save Project"))
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
        self.resize(300, 120)

    def choose_output(self):
        file_name, _ = GetOutputFileName(self, "File Path", ["QGIS Project(*.qgz)"], ".qgz", standard_path())
        self.output_path.setText(file_name)

    def run(self):
        project = QgsProject.instance()
        project.write(self.output_path.text())
        
        self.save_temporary_layers()
        self.finished.emit("projectSaved")
        self.close()

    def save_temporary_layers(self):
        layers = QgsProject.instance().mapLayers().values()
        output_file_path = os.path.join(self.qgis_project.project.project_base_path, "qgis_layers.sqlite")
        file_exists = True if os.path.isfile(output_file_path) else False

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
                    layer.setDataSource(output_file_path + f'|layername={layer.name()}', layer.name(), 'ogr')

                file_exists = True
