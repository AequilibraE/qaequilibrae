import os

from qgis.PyQt import QtCore, QtWidgets
from qgis.core import QgsProject, QgsVectorFileWriter
from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.modules.common_tools import GetOutputFileName


class SaveAsQGZ(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)

    def __init__(self, qgis_project):
        super().__init__()
        self.qgis_project = qgis_project
        self.qgz_project = QgsProject.instance()
        self.layers = self.qgz_project.mapLayers().values()

        self.file_name = self.choose_output()
        self.run()

    def choose_output(self):
        file_name, _ = GetOutputFileName(QtWidgets.QDialog(), "File Path", ["QGIS Project(*.qgz)"], ".qgz", standard_path())
        return file_name

    def save_project(self):
        self.qgz_project.write(self.file_name)
        self.finished.emit("projectSaved")

    def __save_temporary_layers(self, layers):
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
                    layer.setDataSource(output_file_path + f"|layername={layer.name()}", layer.name(), "ogr")

                file_exists = True

    def run(self):
        self.__save_temporary_layers(self.layers)
        self.save_project()
