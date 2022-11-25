import os

import qgis
from ..common_tools import get_vector_layer_by_name
from ..common_tools.global_parameters import multi_line, multi_poly, line_types, point_types, poly_types
from ..common_tools.global_parameters import multi_point
from qgis.PyQt import QtWidgets, uic
from .simple_tag_procedure import SimpleTAG

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_simple_tag.ui"))


class SimpleTagDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QtWidgets.QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.setupUi(self)
        self.valid_layer_types = point_types + line_types + poly_types + multi_poly + multi_line + multi_point
        self.geography_types = [None, None]

        self.fromtype = None
        self.frommatchingtype = None

        self.fromlayer.currentIndexChanged.connect(self.set_from_fields)
        self.tolayer.currentIndexChanged.connect(self.set_to_fields)
        self.fromfield.currentIndexChanged.connect(self.reload_fields)
        self.matchingfrom.currentIndexChanged.connect(self.reload_fields_matching)
        self.needsmatching.stateChanged.connect(self.works_field_matching)

        self.OK.clicked.connect(self.run)

        # We load the node and area layers existing in our canvas
        for layer in qgis.utils.iface.mapCanvas().layers():  # We iterate through all layers
            if "wkbType" in dir(layer):
                if layer.wkbType() in self.valid_layer_types:
                    self.fromlayer.addItem(layer.name())
                    self.tolayer.addItem(layer.name())

        self.enclosed.setToolTip(
            "If source layer is a polygon, source needs to enclose target.  If only target is "
            "a polygon, target needs to enclose source. First found record is used"
        )

        self.touching.setToolTip("Criteria to choose when there are multiple matches is largest area or length matched")
        self.closest.setToolTip("Heuristic procedure that only computes the actual distance to the nearest neighbors")
        self.works_field_matching()

    def reload_fields(self):
        self.matches_types()
        self.set_to_fields()

    def reload_fields_matching(self):
        self.matches_types()
        if self.tolayer.currentIndex() >= 0:
            self.matchingto.clear()
            layer = get_vector_layer_by_name(self.tolayer.currentText())  # If we have the right layer in hands
            for field in layer.fields().toList():
                self.matchingto.addItem(field.name())

    def set_from_fields(self):
        self.fromfield.clear()

        # Decide if it has area:
        if self.fromlayer.currentIndex() >= 0:
            layer = get_vector_layer_by_name(self.fromlayer.currentText())  # If we have the right layer in hands

            for field in layer.fields().toList():
                self.fromfield.addItem(field.name())

            if self.tolayer.currentIndex() >= 0:
                self.set_available_operations()

        if self.needsmatching.isChecked():
            self.works_field_matching()
        self.matches_types()

    def set_to_fields(self):
        self.tofield.clear()

        if self.tolayer.currentIndex() >= 0:
            layer = get_vector_layer_by_name(self.tolayer.currentText())  # If we have the right layer in hands

            for field in layer.fields().toList():
                self.tofield.addItem(field.name())

            if self.fromlayer.currentIndex() >= 0:
                self.set_available_operations()

        if self.needsmatching.isChecked():
            self.works_field_matching()

    def set_available_operations(self):
        # Enclosed is possible every time there is a layer of polygons
        # Touching does not make sense where there are nodes - We do NOT want to take care of the point on line
        #                                                      or on top of point

        # Check if we have polygons

        flayer = get_vector_layer_by_name(self.fromlayer.currentText())
        tlayer = get_vector_layer_by_name(self.tolayer.currentText())

        # polygon layers
        if flayer.wkbType() in poly_types + multi_poly or tlayer.wkbType() in poly_types + multi_poly:
            self.enclosed.setEnabled(True)
        else:
            self.enclosed.setEnabled(False)

        # point layers
        if flayer.wkbType() in point_types + multi_point or tlayer.wkbType() in point_types + multi_point:
            self.touching.setEnabled(False)
        else:
            self.touching.setEnabled(True)

        if flayer.wkbType() in poly_types + multi_poly:
            self.geography_types[0] = "polygon"
        elif flayer.wkbType() in line_types + multi_line:
            self.geography_types[0] = "linestring"
        else:
            self.geography_types[0] = "point"

        if tlayer.wkbType() in poly_types + multi_poly:
            self.geography_types[1] = "polygon"
        elif tlayer.wkbType() in line_types + multi_line:
            self.geography_types[1] = "linestring"
        else:
            self.geography_types[1] = "point"

    def works_field_matching(self):

        self.matchingfrom.clear()
        self.matchingto.clear()

        if self.needsmatching.isChecked():
            self.matchingfrom.setVisible(True)
            self.matchingto.setVisible(True)
            self.lblmatchfrom.setVisible(True)
            self.lblmatchto.setVisible(True)

            if self.fromlayer.currentIndex() >= 0:
                layer = get_vector_layer_by_name(self.fromlayer.currentText())  # If we have the right layer in hands
                for field in layer.fields().toList():
                    self.matchingfrom.addItem(field.name())

            if self.tolayer.currentIndex() >= 0:
                layer = get_vector_layer_by_name(self.tolayer.currentText())  # If we have the right layer in hands
                for field in layer.fields().toList():
                    self.matchingto.addItem(field.name())
        else:
            self.matchingfrom.setVisible(False)
            self.matchingto.setVisible(False)
            self.lblmatchfrom.setVisible(False)
            self.lblmatchto.setVisible(False)

    def matches_types(self):
        self.fromtype = None
        self.frommatchingtype = None

        if self.fromlayer.currentIndex() >= 0:
            layer = get_vector_layer_by_name(self.fromlayer.currentText())  # If we have the right layer in hands
            for field in layer.fields().toList():
                if self.fromfield.currentText() == field.name():
                    self.fromtype = field.type()

        if self.needsmatching.isChecked():
            if self.fromlayer.currentIndex() >= 0:
                layer = get_vector_layer_by_name(self.fromlayer.currentText())  # If we have the right layer in hands
                for field in layer.fields().toList():
                    if self.matchingfrom.currentText() == field.name():
                        self.frommatchingtype = field.type()

    def run_thread(self):
        self.worker_thread.ProgressValue.connect(self.progress_value_from_thread)
        self.worker_thread.ProgressMaxValue.connect(self.progress_range_from_thread)
        self.worker_thread.ProgressText.connect(self.progress_text_from_thread)
        self.worker_thread.finished_threaded_procedure.connect(self.finished_threaded_procedure)

        self.OK.setEnabled(False)
        self.worker_thread.start()
        self.exec_()

    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val)

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value)

    def progress_text_from_thread(self, value):
        self.lbl_operation.setText(value)

    def finished_threaded_procedure(self, procedure):
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage(
                "Input data not provided correctly", self.worker_thread.error, level=3
            )
        self.close()

    def run(self):
        error = False
        for wdgt in [self.fromlayer, self.fromfield, self.tolayer, self.tofield]:
            if wdgt.currentIndex() < 0:
                error = True

        if self.needsmatching.isChecked():
            if self.matchingfrom.currentIndex() < 0 or self.matchingto.currentIndex() < 0:
                error = True

        flayer = self.fromlayer.currentText()
        ffield = self.fromfield.currentText()

        tlayer = self.tolayer.currentText()
        tfield = self.tofield.currentText()

        fmatch = None
        tmatch = None
        if self.needsmatching.isChecked():
            fmatch = self.matchingfrom.currentText()
            tmatch = self.matchingto.currentText()

        if self.enclosed.isChecked():
            operation = "ENCLOSED"
        elif self.touching.isChecked():
            operation = "TOUCHING"
        else:
            operation = "CLOSEST"

        if not error:
            self.worker_thread = SimpleTAG(
                qgis.utils.iface.mainWindow(),
                flayer,
                tlayer,
                ffield,
                tfield,
                fmatch,
                tmatch,
                operation,
                self.geography_types,
            )
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Input data not provided correctly", "  Try again", level=3)


def unload(self):
    pass
