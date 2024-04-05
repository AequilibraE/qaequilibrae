import os
from uuid import uuid4

from qgis.PyQt import QtCore, QtWidgets
from qgis.core import QgsProject, QgsVectorFileWriter, QgsExpressionContextUtils
from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.modules.common_tools import GetOutputFileName


class SaveAsQGZ(QtCore.QObject):
    finished = QtCore.pyqtSignal(object)

    def __init__(self, qgis_project):
        super().__init__()
        self.qgis_project = qgis_project
        self.qgz_project = QgsProject.instance()
        
        self.prj_path = self.qgis_project.project.project_base_path
        self.output_file_path = os.path.join(self.prj_path, "qgis_layers.sqlite")
        self.file_exists = True if os.path.isfile(self.output_file_path) else False

        if not self.file_exists:
            self.file_name = self.choose_output()

        self.run()

    def choose_output(self):
        file_name, _ = GetOutputFileName(
            QtWidgets.QDialog(), "File Path", ["QGIS Project(*.qgz)"], ".qgz", standard_path()
        )
        return file_name

    def save_project(self):
        if "aequilibrae_path" not in self.qgz_project.customVariables():
            QgsExpressionContextUtils.setProjectVariable(self.qgz_project, 'aequilibrae_path', self.prj_path)
            self.qgz_project.write(self.file_name)
        else:
            self.qgz_project.write()
        self.finished.emit("projectSaved")

    def run(self):
        SaveTempLayers(self.output_file_path, self.qgz_project, self.file_exists)
        self.save_project()


class SaveTempLayers:
    def __init__(self, path, proj_instance, file_exists):
        self.save_temp_layers_to_db(path, proj_instance, file_exists)

    def save_temp_layers_to_db(self, path, proj_instance, file_exists):
        for layer in proj_instance.mapLayers().values():
            if layer.isTemporary():
                layer_name = layer.name() + f"_{uuid4().hex}"
                print("temp: ", layer.name())
                options = QgsVectorFileWriter.SaveVectorOptions()
                options.driverName = "SQLite"
                options.layerName = layer_name
                if file_exists:
                    options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

                transform_context = QgsProject.instance().transformContext()

                error = QgsVectorFileWriter.writeAsVectorFormatV3(layer, path, transform_context, options)

                if error[0] == QgsVectorFileWriter.NoError:
                    layer.setDataSource(path + f"|layername={layer_name}", layer.name(), "ogr")

                file_exists = True
