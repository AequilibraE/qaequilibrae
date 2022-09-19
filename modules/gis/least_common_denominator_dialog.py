import os
from functools import partial

import qgis
from ..common_tools.global_parameters import poly_types, multi_poly, point_types
from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsProject
from .least_common_denominator_procedure import LeastCommonDenominatorProcedure
from ..common_tools import get_vector_layer_by_name

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_least_common_denominator.ui"))


class LeastCommonDenominatorDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QtWidgets.QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.setupUi(self)

        # The whole software is prepared to deal with all geometry types, but it has only been tested to work with
        # polygons, so I am turning the other layer types off
        # self.valid_layer_types = point_types + line_types + poly_types + multi_poly + multi_line + multi_point
        self.valid_layer_types = poly_types + multi_poly

        self.fromlayer.currentIndexChanged.connect(partial(self.reload_fields, "from"))
        self.tolayer.currentIndexChanged.connect(partial(self.reload_fields, "to"))
        self.OK.clicked.connect(self.run)

        # We load the node and area layers existing in our canvas
        for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
            if "wkbType" in dir(layer):
                if layer.wkbType() in self.valid_layer_types:
                    self.fromlayer.addItem(layer.name())
                    self.tolayer.addItem(layer.name())

    def reload_fields(self, box):
        if box == "from":
            self.fromfield.clear()
            if self.fromlayer.currentIndex() >= 0:
                layer = get_vector_layer_by_name(self.fromlayer.currentText())  # If we have the right layer in hands
                for field in layer.fields().toList():
                    self.fromfield.addItem(field.name())
        else:
            self.tofield.clear()
            if self.tolayer.currentIndex() >= 0:
                layer = get_vector_layer_by_name(self.tolayer.currentText())  # If we have the right layer in hands
                for field in layer.fields().toList():
                    self.tofield.addItem(field.name())

    def run_thread(self):
        self.worker_thread.ProgressValue.connect(self.progress_value_from_thread)
        self.worker_thread.ProgressMaxValue.connect(self.progress_range_from_thread)
        self.worker_thread.ProgressText.connect(self.progress_text_from_thread)

        self.worker_thread.finished_threaded_procedure.connect(self.finished_threaded_procedure)
        self.OK.setEnabled(False)
        self.worker_thread.start()
        self.exec_()

    def progress_range_from_thread(self, value):
        self.progressbar.setRange(0, value)

    def progress_text_from_thread(self, value):
        self.progress_label.setText(value)

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value)

    def finished_threaded_procedure(self, procedure):
        if self.worker_thread.error is None:
            QgsProject.instance().addMapLayer(self.worker_thread.result)
        else:
            qgis.utils.iface.messageBar().pushMessage(
                "Input data not provided correctly", self.worker_thread.error, level=3
            )
        self.close()

    def run(self):
        error = None
        if (
            self.fromlayer.currentIndex() < 0
            or self.fromfield.currentIndex() < 0
            or self.tolayer.currentIndex() < 0
            or self.tofield.currentIndex() < 0
        ):
            error = "ComboBox with ilegal value"

        flayer = self.fromlayer.currentText()
        ffield = self.fromfield.currentText()
        tlayer = self.tolayer.currentText()
        tfield = self.tofield.currentText()

        layer1 = get_vector_layer_by_name(self.fromlayer.currentText()).wkbType()
        layer2 = get_vector_layer_by_name(self.tolayer.currentText()).wkbType()
        if layer1 in point_types and layer2 in point_types:
            error = "It is not sensible to have two point layers for this analysis"

        if error is None:
            self.worker_thread = LeastCommonDenominatorProcedure(
                qgis.utils.iface.mainWindow(), flayer, tlayer, ffield, tfield
            )
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Input data not provided correctly. ", error, level=3)
