import os
import sys
from functools import partial

import qgis
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog
from qgis.core import QgsStyle

sys.modules["qgsfieldcombobox"] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_bandwidth_color_ramps.ui"))


class LoadColorRampSelector(QDialog, FORM_CLASS):
    def __init__(self, iface, layer):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.layer = layer
        myStyle = QgsStyle().defaultStyle()

        self.defaultColorRampNames = myStyle.colorRampNames()

        for i in self.defaultColorRampNames:
            self.cbb_ab_color.addItem(i)
            self.cbb_ba_color.addItem(i)
        index = 0
        self.cbb_ab_color.setCurrentIndex(index)
        self.cbb_ba_color.setCurrentIndex(index)
        self.resize(341, 238)
        self.cbb_ba_field.setLayer(layer)

        self.but_done.clicked.connect(self.load_ramps)
        self.but_cancel.clicked.connect(self.exit_procedure)

        self.cbb_ab_field.currentIndexChanged.connect(partial(self.change_field, "AB"))
        self.cbb_ba_field.currentIndexChanged.connect(partial(self.change_field, "BA"))

        self.chk_dual_fields.stateChanged.connect(self.set_dual_fields)

        self.set_dual_fields()
        self.change_field("AB")
        self.results = None

    def load_ramps(self):
        self.results = {}
        self.results["color ab"] = self.cbb_ab_color.currentText()
        self.results["max ab"] = float(self.txt_ab_max.text())
        self.results["min ab"] = float(self.txt_ab_min.text())

        if self.chk_dual_fields.isChecked():
            self.results["max ba"] = self.results["max ab"]
            self.results["min ba"] = self.results["min ab"]
            self.results["color ba"] = self.results["color ab"]

            self.results["ramp ab"] = self.cbb_ab_field.currentText().replace("_*", "_ab")
            self.results["ramp ba"] = self.cbb_ab_field.currentText().replace("_*", "_ba")

        else:
            self.results["ramp ab"] = self.cbb_ab_field.currentText()
            self.results["ramp ba"] = self.cbb_ab_field.currentText()
            self.results["color ba"] = self.cbb_ba_color.currentText()
            self.results["max ba"] = float(self.txt_ba_max.text())
            self.results["min ba"] = float(self.txt_ba_min.text())
        self.exit_procedure()

    def change_field(self, direction):
        def set_values_to_boxes(minval, min_box, maxval, max_box):
            min_box.setText(str(minval))
            max_box.setText(str(maxval))

        def find_max_min(field):
            idx = self.layer.fields().indexFromName(field)
            minval, maxval = self.layer.minimumAndMaximumValue(idx)
            minval = round(0 if minval is None else minval, 2)
            maxval = round(0 if maxval is None else maxval, 2)
            return minval, maxval

        if direction == "BA":
            if self.cbb_ba_field.currentIndex() > 0:
                minval, maxval = find_max_min(self.cbb_ba_field.currentText())
                set_values_to_boxes(minval, self.txt_ba_min, maxval, self.txt_ba_max)

        else:
            if self.cbb_ab_field.currentIndex() > 0:
                if self.chk_dual_fields.isChecked():
                    field_ab = self.cbb_ab_field.currentText().replace("_*", "_ab")
                    field_ba = self.cbb_ab_field.currentText().replace("_*", "_ba")
                    minval, maxval = find_max_min(field_ab)
                    minval1, maxval2 = find_max_min(field_ba)
                    minval = min(minval, minval1)
                    maxval = max(maxval, maxval2)
                    set_values_to_boxes(minval, self.txt_ab_min, maxval, self.txt_ab_max)
                else:
                    minval, maxval = find_max_min(self.cbb_ab_field.currentText())
                    set_values_to_boxes(minval, self.txt_ab_min, maxval, self.txt_ab_max)

    def set_dual_fields(self):
        if self.chk_dual_fields.isChecked():
            self.hide_fields(False)
        else:
            self.hide_fields(True)

    def hide_fields(self, action):
        self.cbb_ba_field.setEnabled(action)
        self.cbb_ba_color.setEnabled(action)
        self.txt_ba_min.setEnabled(action)
        self.txt_ba_max.setEnabled(action)
        self.label_3.setEnabled(action)
        self.label_4.setEnabled(action)
        if action:
            self.resize(589, 238)
            self.cbb_ab_field.clear()
            for field in self.layer.fields().names():
                self.cbb_ab_field.addItem(field)
        else:
            self.resize(341, 238)
            self.cbb_ab_field.clear()
            fields = self.layer.fields().names()
            for field in fields:
                if "_ab" in field:
                    if field.replace("_ab", "_ba") in fields:
                        fields.remove(field.replace("_ab", "_ba"))
                        field = field.replace("_ab", "_*")
                        self.cbb_ab_field.addItem(field)
                if "_ba" in field:
                    if field.replace("_ba", "_ab") in fields:
                        fields.remove(field.replace("_ba", "_ab"))
                        field = field.replace("_ba", "_*")
                        self.cbb_ab_field.addItem(field)
                else:
                    self.cbb_ab_field.addItem(field)

        # self.cbb_ba_color.setVisible(False)

    def exit_procedure(self):
        self.close()
