import os
import sqlite3
import sys
from functools import partial
from os.path import join

from qgis._core import QgsExpressionContextUtils, QgsLineSymbol, QgsSimpleLineSymbolLayer

import qgis
from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.core import QgsExpression
from qgis.core import QgsProject
from qgis.core import QgsVectorLayerJoinInfo
from ..common_tools import get_parameter_chain
from ..common_tools import find_table_fields
from ..matrix_procedures.load_result_table import load_result_table
from ..matrix_procedures import list_results

sys.modules["qgsfieldcombobox"] = qgis.gui
sys.modules["qgsmaplayercombobox"] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_compare_scenarios.ui"))


class CompareScenariosDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QtWidgets.QDialog.__init__(self)
        self.qgis_project = qgis_project
        self.iface = qgis_project.iface
        self.setupUi(self)
        self.conn = sqlite3.connect(join(qgis_project.project.project_base_path, "results_database.sqlite"))
        self.positive_color.setColor(QtGui.QColor(0, 174, 116, 255))
        self.negative_color.setColor(QtGui.QColor(218, 0, 3, 255))
        self.common_flow_color.setColor(QtGui.QColor(0, 0, 0, 255))
        self.radio_diff.toggled.connect(self.show_color_composite)
        self.radio_compo.toggled.connect(self.show_color_composite)

        self.results = list_results(self.qgis_project.project.project_base_path)

        self.band_size = 10.0
        self.space_size = 0.0
        self.link_layer = None
        self.drive_side = get_parameter_chain(["system", "driving side"])

        # space slider
        self.slider_spacer.setMinimum(0)
        self.slider_spacer.setMaximum(30)
        self.slider_spacer.setValue(0)
        self.slider_spacer.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.slider_spacer.setTickInterval(10)
        self.slider_spacer.valueChanged.connect(self.spacevaluechange)
        self.cob_base_scenario.currentIndexChanged.connect(
            partial(self.choose_scenario, self.cob_base_scenario, self.cob_base_data)
        )
        self.cob_alternative_scenario.currentIndexChanged.connect(
            partial(self.choose_scenario, self.cob_alternative_scenario, self.cob_alternative_data)
        )

        # band slider
        self.slider_band_size.setMinimum(5)
        self.slider_band_size.setMaximum(150)
        self.slider_band_size.setValue(50)
        self.slider_band_size.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.slider_band_size.setTickInterval(5)
        self.slider_band_size.valueChanged.connect(self.sizevaluechange)
        self.mode_frame.setVisible(False)
        self.but_run.clicked.connect(self.execute_comparison)
        self.add_fields_to_cboxes()
        self.sizevaluechange()
        self.spacevaluechange()
        self.show_color_composite()
        self.base_group_box.setToolTip("This is the reference case, to which the differences will refer to")
        self.alt_group_box.setToolTip("This is the alternative")
        self.color_group_box.setToolTip("It will be BASE minus ALTERNATIVE")

    def show_color_composite(self):
        self.common_label.setVisible(self.radio_compo.isChecked())
        self.common_flow_color.setVisible(self.radio_compo.isChecked())

    def spacevaluechange(self):
        self.space_size = self.slider_spacer.value() / 100.0
        self.lbl_space.setText("{:3,.2f}".format(self.space_size))

    def sizevaluechange(self):
        self.band_size = self.slider_band_size.value() / 5.0
        self.lbl_width.setText("{:3,.2f}".format(self.band_size))

    def add_fields_to_cboxes(self):
        data = list(self.results[self.results.WARNINGS == ""].table_name)
        for cob in [self.cob_base_scenario, self.cob_alternative_scenario]:
            cob.clear()
            cob.addItems(data)

    def choose_scenario(self, cob_scenario, cob_fields):
        cob_fields.clear()
        if cob_scenario.currentIndex() < 0:
            return
        lst = find_table_fields(self.conn, cob_scenario.currentText())
        flds = [x.replace("ab", "*") for x in lst if "ab" in x and x.replace("ab", "ba") in lst]
        cob_fields.addItems(flds)

    def execute_comparison(self):
        if not self.check_inputs():
            return

        self.but_run.setEnabled(False)
        self.band_size = str(self.band_size)
        self.space_size = str(self.space_size)

        QgsExpressionContextUtils.setProjectVariable(QgsProject.instance(), "aeq_band_spacer", float(self.space_size))
        QgsExpressionContextUtils.setProjectVariable(QgsProject.instance(), "aeq_band_width", float(self.band_size))
        self.space_size = "@aeq_band_spacer"
        self.band_size = "@aeq_band_width"

        # define the side of the plotting based on the side of the road the system has defined
        ab = 1 if self.drive_side == "right" else -1
        ba = -ab

        # fields
        [ab_base, ba_base], [ab_alt, ba_alt] = self.load_result_tables()

        # Create new simple stype
        symbol = QgsLineSymbol.createSimple({"name": "square", "color": "red"})
        self.link_layer.renderer().setSymbol(symbol)

        # Create the bandwidths for the common flow, if requested
        if self.radio_compo.isChecked():
            exp = QgsExpression(
                f"""max(maximum(coalesce("{ab_base}",0)),
                                        maximum(coalesce("{ab_alt}",0)),
                                        maximum(coalesce("{ba_base}",0)),
                                        maximum(coalesce("{ba_alt}",0))) """
            )
            context = self.link_layer.createExpressionContext()
            max_value = exp.evaluate(context).real

            QgsExpressionContextUtils.setProjectVariable(QgsProject.instance(), "aeq_band_max_value", float(max_value))
            max_value = "@aeq_band_max_value"

            # We create the styles for AB and BA directions and add to the fields
            text_color = self.text_color(self.common_flow_color)
            for abb, aba, di, t in ([ab_base, ab_alt, ab, "ab"], [ba_base, ba_alt, ba, "ba"]):
                width = f'(coalesce(scale_linear(min("{abb}","{aba}") , 0,{max_value},0,{self.band_size}), 0))'
                offset = f"{di}*({width}/2 + {self.space_size})"
                line_pattern = f'if (max(coalesce("{abb}"+"{aba}", 0),0) = 0,' + "'no', 'solid')"
                symbol_layer = self.create_style(width, offset, text_color, line_pattern)
                self.link_layer.renderer().symbol().appendSymbolLayer(symbol_layer)
                ab_offset = offset if t == "ab" else None
                ba_offset = offset if t != "ab" else None

        # If we want a plot of the differences only
        if self.radio_diff.isChecked():
            exp = QgsExpression(
                f"""max(maximum(abs(coalesce("{ab_base}",0)-coalesce("{ab_alt}",0))),
                                        maximum(abs(coalesce("{ba_base}",0)-coalesce("{ba_alt}",0)))) """
            )
            context = self.link_layer.createExpressionContext()
            max_value = exp.evaluate(context).real
            ab_offset = ba_offset = "0"

            QgsExpressionContextUtils.setProjectVariable(QgsProject.instance(), "aeq_band_max_value", float(max_value))
            max_value = "@aeq_band_max_value"

        # We now create the positive and negative bandwidths for each side of the link
        styles = []
        styles.append((ab_base, ab_alt, ab, ab_offset))
        styles.append((ba_base, ba_alt, ba, ba_offset))

        pos_color = self.text_color(self.positive_color)
        neg_color = self.text_color(self.negative_color)

        for i in styles:
            width = f'(coalesce(scale_linear(abs("{i[0]}"-"{i[1]}") , 0,{max_value},0,{self.band_size}),0))'
            offset = f"{i[3]}+{i[2]}*({width}/2 + {self.space_size})"
            line_pattern = f'if (coalesce("{i[0]}"-"{i[1]}", 0) = 0,' + "'no', 'solid')"
            color = f'if(max(("{i[0]}"-"{i[1]}"),0) = 0,{neg_color},{pos_color})'
            symbol_layer = self.create_style(width, offset, color, line_pattern)
            self.link_layer.renderer().symbol().appendSymbolLayer(symbol_layer)

        # Deletes the pre-existing style
        self.link_layer.renderer().symbol().deleteSymbolLayer(0)
        self.link_layer.triggerRepaint()
        self.exit_procedure()

    def check_inputs(self):
        for combo in [
            self.cob_base_scenario,
            self.cob_alternative_scenario,
            self.cob_base_data,
            self.cob_alternative_data,
        ]:
            if combo.currentIndex() < 0:
                return False

        v1 = self.cob_base_scenario.currentText()
        v2 = self.cob_alternative_scenario.currentText()
        v3 = self.cob_base_data.currentText()
        v4 = self.cob_alternative_data.currentText()
        if v1 == v2 and v3 == v4:
            return False
        return True

    def load_result_tables(self):
        self.link_layer = self.qgis_project.layers["links"][0]
        QgsProject.instance().addMapLayer(self.link_layer)

        v1 = self.cob_base_scenario.currentText()
        v2 = self.cob_alternative_scenario.currentText()
        v3 = self.cob_base_data.currentText()
        v4 = self.cob_alternative_data.currentText()
        self.base_lyr = load_result_table(self.qgis_project.project.project_base_path, v1)
        data_to_join = [[self.base_lyr, "base"]]

        txt = f"base_{v3}"
        data_fields = [[txt.replace("*", "ab"), txt.replace("*", "ba")]]
        txt = f"base_{v4}"
        if v1 != v2:
            self.alter_layer = load_result_table(self.qgis_project.project.project_base_path, v2)
            data_to_join.append([self.alter_layer, "alternative"])
            txt = f"alternative_{v4}"
        data_fields.append([txt.replace("*", "ab"), txt.replace("*", "ba")])

        for lyr, nm in data_to_join:
            lien = QgsVectorLayerJoinInfo()
            lien.setJoinFieldName("link_id")
            lien.setTargetFieldName("link_id")
            lien.setJoinLayerId(lyr.id())
            lien.setUsingMemoryCache(True)
            lien.setJoinLayer(lyr)
            lien.setPrefix(f"{nm}_")
            self.link_layer.addJoin(lien)
        return data_fields

    def create_style(self, width, offset, color, line_pattern):
        symbol_layer = QgsSimpleLineSymbolLayer.create({})
        props = symbol_layer.properties()
        props["width_dd_expression"] = width
        props["offset_dd_expression"] = offset
        props["line_style_expression"] = line_pattern
        props["color_dd_expression"] = color
        symbol_layer = QgsSimpleLineSymbolLayer.create(props)
        return symbol_layer

    def exit_procedure(self):
        self.close()

    def text_color(self, some_color_btn):
        str_color = str(some_color_btn.color().getRgb())
        str_color = str_color.replace("(", "")
        return "'" + str_color.replace(")", "") + "'"
