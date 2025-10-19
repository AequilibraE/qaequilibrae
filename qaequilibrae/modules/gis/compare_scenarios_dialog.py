import sys
from functools import partial
from os.path import dirname, join

import qgis
from qgis.PyQt import QtGui, QtWidgets
from qgis.core import QgsExpression, QgsProject
from qgis.core import QgsExpressionContextUtils, QgsLineSymbol, QgsSimpleLineSymbolLayer

from qaequilibrae.modules.common_tools import BaseDialog
from qaequilibrae.modules.common_tools import find_table_fields, get_parameter_chain, layer_from_geodataframe
from qaequilibrae.modules.matrix_procedures import list_results, load_result_table

sys.modules["qgsfieldcombobox"] = qgis.gui
sys.modules["qgsmaplayercombobox"] = qgis.gui


class CompareScenariosDialog(BaseDialog):
    def __init__(self, qgis_project):
        super().__init__(ui_file=join(dirname(__file__), "forms/ui_compare_scenarios.ui"), qgis_project=qgis_project)

    def _base_ui_setup(self):

        self.positive_color.setColor(QtGui.QColor(0, 174, 116, 255))
        self.negative_color.setColor(QtGui.QColor(218, 0, 3, 255))
        self.common_flow_color.setColor(QtGui.QColor(0, 0, 0, 255))
        self.radio_diff.toggled.connect(self.show_color_composite)
        self.radio_compo.toggled.connect(self.show_color_composite)

        self.results = list_results(self.qgis_project.project)

        self.__init_scenario = self.qgis_project.cob_scenarios.currentText()

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
            partial(self.choose_scenario, self.cob_base_scenario, self.cob_base_result)
        )
        self.cob_alt_scenario.currentIndexChanged.connect(
            partial(self.choose_scenario, self.cob_alt_scenario, self.cob_alternative_result)
        )
        self.cob_base_result.currentIndexChanged.connect(
            partial(self.choose_result, self.cob_base_scenario, self.cob_base_result, self.cob_base_data)
        )
        self.cob_alternative_result.currentIndexChanged.connect(
            partial(self.choose_result, self.cob_alt_scenario, self.cob_alternative_result, self.cob_alternative_data)
        )

        # band slider
        self.slider_band_size.setMinimum(5)
        self.slider_band_size.setMaximum(150)
        self.slider_band_size.setValue(50)
        self.slider_band_size.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.slider_band_size.setTickInterval(5)
        self.slider_band_size.valueChanged.connect(self.sizevaluechange)
        self.but_run.clicked.connect(self.execute_comparison)
        self.add_fields_to_cboxes()
        self.sizevaluechange()
        self.spacevaluechange()
        self.show_color_composite()
        self.base_group_box.setToolTip(self.tr("This is the reference case, to which the differences will refer to"))
        self.alt_group_box.setToolTip(self.tr("This is the alternative"))
        self.color_group_box.setToolTip(self.tr("It will be BASE minus ALTERNATIVE"))

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
        for cob in [self.cob_base_scenario, self.cob_alt_scenario]:
            cob.clear()
            cob.addItems(self.qgis_project.available_scenarios)

    def choose_scenario(self, cob_scenario, cob_results):
        cob_results.clear()
        if cob_scenario.currentIndex() < 0:
            return
        if self.__init_scenario != cob_scenario.currentText():
            self.qgis_project.project.use_scenario(cob_scenario.currentText())
        flds = self.qgis_project.project.results.list()["table_name"].tolist()
        if self.__init_scenario != cob_scenario.currentText():
            self.qgis_project.project.use_scenario(self.__init_scenario)
        cob_results.addItems(flds)

    def choose_result(self, cob_scenario, cob_results, cob_fields):
        cob_fields.clear()
        if cob_results.currentIndex() < 0:
            return
        if self.__init_scenario != cob_scenario.currentText():
            self.qgis_project.project.use_scenario(cob_scenario.currentText())
        with self.qgis_project.project.results_connection as conn:
            lst = find_table_fields(conn, cob_results.currentText())
        if self.__init_scenario != cob_scenario.currentText():
            self.qgis_project.project.use_scenario(self.__init_scenario)
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
            self.cob_alt_scenario,
            self.cob_base_result,
            self.cob_alternative_result,
            self.cob_base_data,
            self.cob_alternative_data,
        ]:
            if combo.currentIndex() < 0:
                return False

        v1 = self.cob_base_scenario.currentText()
        v2 = self.cob_alt_scenario.currentText()
        v3 = self.cob_base_result.currentText()
        v4 = self.cob_alternative_result.currentText()
        v5 = self.cob_base_data.currentText()
        v6 = self.cob_alternative_data.currentText()
        if v1 == v2 and v3 == v4 and v5 == v6:
            return False
        return True

    def load_result_tables(self):
        """ """
        columns = ["link_id", "a_node", "b_node", "geometry"]

        v1 = self.cob_base_scenario.currentText()
        v2 = self.cob_alt_scenario.currentText()
        v3 = self.cob_base_result.currentText()
        v4 = self.cob_alternative_result.currentText()
        v5 = self.cob_base_data.currentText()
        v6 = self.cob_alternative_data.currentText()

        # Load base scenario data
        if v1 != self.__init_scenario:
            self.qgis_project.project.use_scenario(v1)
        base_links = self.qgis_project.project.network.links.data
        base_links = base_links[columns]
        base_lyr_result = load_result_table(self.qgis_project.project, v3)
        base_cols = ["link_id"]
        base_cols.extend([x for x in base_lyr_result.columns if v5[:-1] in x and "_tot" not in x])

        # Load alternative scenario data
        if v1 != v2:
            self.qgis_project.project.use_scenario(v2)
        alter_links = self.qgis_project.project.network.links.data
        alter_links = alter_links[columns]
        alter_lyr_result = load_result_table(self.qgis_project.project, v4)
        alter_cols = ["link_id"]
        alter_cols.extend([x for x in alter_lyr_result.columns if v6[:-1] in x and "_tot" not in x])

        # Go back to the currently selected scenario
        self.qgis_project.project.use_scenario(self.__init_scenario)

        # Join base links with results
        base_links = base_links.merge(base_lyr_result[base_cols], on="link_id")
        base_links.columns = [f"base_{x}" if "geometry" not in x else "geometry" for x in base_links.columns]

        # Join anternative links with results
        alter_links = alter_links.merge(alter_lyr_result[alter_cols], on="link_id")
        alter_links.columns = [f"alternative_{x}" if "geometry" not in x else "geometry" for x in alter_links.columns]

        txt = f"base_{v5}"
        data_fields = [[txt.replace("*", "ab"), txt.replace("*", "ba")]]
        values = {txt.replace("*", "ab"): 0, txt.replace("*", "ba"): 0}
        txt = f"alternative_{v6}"
        data_fields.append([txt.replace("*", "ab"), txt.replace("*", "ba")])
        values[txt.replace("*", "ab")] = 0
        values[txt.replace("*", "ba")] = 0

        base_cols = ["base_link_id", "base_a_node", "base_b_node", "geometry"]
        alter_cols = ["alternative_link_id", "alternative_a_node", "alternative_b_node", "geometry"]

        links = base_links.merge(alter_links, left_on=base_cols, right_on=alter_cols, how="outer")

        link_cols = links.columns.tolist()
        link_cols.remove("geometry")
        link_cols.append("geometry")
        links = links[link_cols]
        links.fillna(value=values, inplace=True)

        self.link_layer = layer_from_geodataframe(links, "scenario_comparison")

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
