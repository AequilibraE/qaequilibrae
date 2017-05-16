"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Main interface for creating a TranspoNet from layers previously prepared
 Purpose:    Load GUI and user interface for TranspoNet creation

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE
 Transponet Repository: https://github.com/AequilibraE/TranspoNet

 Created:    2017-04-28
 Updated:    2017-05-03
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import qgis
from qgis.core import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
import sys
from qgis.gui import QgsMapLayerProxyModel
import os
from ..common_tools.global_parameters import *
from ..common_tools import GetOutputFileName
from ..common_tools.auxiliary_functions import *
from ..common_tools import ReportDialog
from functools import partial
from creates_transponet_procedure import CreatesTranspoNetProcedure

sys.modules['qgsmaplayercombobox'] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'forms/ui_transponet_construction.ui'))

class CreatesTranspoNetDialog(QDialog, FORM_CLASS):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.path = standard_path()

        self.required_fields_links = ['link_id', 'a_node', 'b_node', 'direction', 'length', 'capacity_ab',
                                      'capacity_ba', 'speed_ab', 'speed_ba']

        self.required_fields_nodes = ['node_id']

        self.link_layer = False
        self.node_layer = False
        self.but_create_network_file.clicked.connect(self.create_net)
        self.counter = {}
        self.output_file = False
        self.error = None
        self.node_layers_list.layerChanged.connect(partial (self.changed_layer, 'nodes'))
        self.node_layers_list.setFilters(QgsMapLayerProxyModel.PointLayer)

        self.link_layers_list.layerChanged.connect(partial (self.changed_layer, 'links'))
        self.link_layers_list.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.node_fields = []
        self.link_fields = []
        self.node_field_indices = {}
        self.link_field_indices = {}
        self.report = None

        if self.node_layers_list.currentIndex() >= 0:
            self.changed_layer('nodes')
        if self.link_layers_list.currentIndex() >= 0:
            self.changed_layer('links')

        self.progressbar.setVisible(False)
        self.progress_label.setVisible(False)

    def changed_layer(self, layer_type):

        layer_fields = None
        if layer_type == 'nodes':
            table = self.table_node_fields
            self.node_layer = get_vector_layer_by_name(self.node_layers_list.currentText())
            if self.node_layer:
                layer_fields = self.node_layer.pendingFields()
        if layer_type == 'links':
            table = self.table_link_fields
            self.link_layer = get_vector_layer_by_name(self.link_layers_list.currentText())
            if self.link_layer:
                layer_fields = self.link_layer.pendingFields()

        table.clearContents()
        # We create the comboboxes that will hold the definitions for all the fields that are mandatory for
        # creating the appropriate triggers on the SQLite file
        if layer_fields:
            fields = [field.name() for field in layer_fields]

            def centers_item(item):
                cell_widget = QWidget()
                lay_out = QHBoxLayout(cell_widget)
                lay_out.addWidget(item)
                lay_out.setAlignment(Qt.AlignCenter)
                lay_out.setContentsMargins(0, 0, 0, 0)
                cell_widget.setLayout(lay_out)
                return cell_widget

            counter = 0
            for field in fields:
                table.setRowCount(counter + 1)
                item1 = QTableWidgetItem(field)
                item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                table.setItem(counter, 0, item1)

                item2 = QTableWidgetItem(field)
                item2.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                table.setItem(counter, 2, item2)

                chb1 = QCheckBox()
                chb1.stateChanged.connect(partial(self.set_field_to_default, layer_type))
                table.setCellWidget(counter, 1, centers_item(chb1))

                chb2 = QCheckBox()
                chb2.setChecked(True)
                chb2.stateChanged.connect(partial(self.set_field_to_keep, layer_type))
                table.setCellWidget(counter, 3, centers_item(chb2))
                counter += 1

            self.counter[layer_type] = counter

    def find_similar_texts_in_combobox(self, text, comb):
        index = comb.findText(text, Qt.MatchFixedString)
        if index >= 0:
            comb.setCurrentIndex(index)
        else:
            index = comb.findText(text[0:min(5,len(text))], Qt.MatchFixedString)
            if index >= 0:
                comb.setCurrentIndex(index)
            else:
                # We treat special cases
                if text.lower() == "dir":
                    text = 'direction'
                if text.lower() == 'id':
                    index = comb.findText('link_id', Qt.MatchFixedString)
                    if index >= 0:
                        text = 'link_id'
                    index = comb.findText('node_id', Qt.MatchFixedString)
                    if index >= 0:
                        text = 'link_id'
                index = comb.findText(text, Qt.MatchFixedString)
                if index >= 0:
                    comb.setCurrentIndex(index)

    def set_field_to_default(self, layer_type):
        if layer_type == 'nodes':
            table = self.table_node_fields
            self.node_layer = get_vector_layer_by_name(self.node_layers_list.currentText())
            required_fields = self.required_fields_nodes
        else:
            table = self.table_link_fields
            self.link_layer = get_vector_layer_by_name(self.link_layers_list.currentText())
            required_fields = self.required_fields_links

        def centers_item(item):
            cell_widget = QWidget()
            lay_out = QHBoxLayout(cell_widget)
            lay_out.addWidget(item)
            lay_out.setAlignment(Qt.AlignCenter)
            lay_out.setContentsMargins(0, 0, 0, 0)
            cell_widget.setLayout(lay_out)
            return cell_widget

        ch_box = self.sender()
        parent = ch_box.parent()
        for i in range(self.counter[layer_type]):
            if table.cellWidget(i, 1) is parent:
                row = i
                break

        if not ch_box.isChecked():
            table.setCellWidget(row, 2, QWidget())
            table.setItem(row, 2, QTableWidgetItem(table.item(row, 0).text()))
        else:
            table.setItem(row, 2, QTableWidgetItem(""))
            for i, q in enumerate(table.cellWidget(row, 3).findChildren(QCheckBox)):
                q.setChecked(True)

            cbb = QComboBox()
            for i in required_fields:
                cbb.addItem(i)

            text = table.item(row, 0).text()
            self.find_similar_texts_in_combobox(text, cbb)
            table.setCellWidget(row, 2, centers_item(cbb))


    def set_field_to_keep(self, layer_type):
        if layer_type == 'nodes':
            table = self.table_node_fields
        else:
            table = self.table_link_fields

        ch_box = self.sender()
        if not ch_box.isChecked():
            parent = ch_box.parent()
            for i in range(self.counter[layer_type]):
                if table.cellWidget(i, 3) is parent:
                    row = i
                    break

            for i, q in enumerate(table.cellWidget(row, 1).findChildren(QCheckBox)):
                if q.isChecked():
                    q.setChecked(False)

    def create_net(self):
        if self.consistency_checks():
            self.output_file, file_type = GetOutputFileName(self, 'TranspoNet', ["SQLite(*.sqlite)"], ".sqlite",
                                                            self.path)

            parameters = [self.output_file,
                          self.node_fields,
                          self.link_fields,
                          self.node_layer,
                          self.required_fields_nodes,
                          self.node_field_indices,
                          self.link_layer,
                          self.required_fields_links,
                          self.link_field_indices]

            self.but_create_network_file.setVisible(False)
            self.progressbar.setVisible(True)
            self.progress_label.setVisible(True)
            self.worker_thread = CreatesTranspoNetProcedure(qgis.utils.iface.mainWindow(), *parameters)
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Missing mandatory fields settings", self.error, level=3,
                                                      duration=3)

    def consistency_checks(self):
        passed_checks = True
        self.error = []
        def compile_fields(layer, table, layer_type):
            name_fields = []
            name_field_indices = {}
            for row in range(self.counter[layer_type]):
                for q in table.cellWidget(row, 3).findChildren(QCheckBox):
                    if q.isChecked():
                        for j in table.cellWidget(row, 1).findChildren(QCheckBox):
                            if j.isChecked(): #we have a default field
                                widget = table.cellWidget(row, 2).findChildren(QComboBox)[0]
                                name_fields.append(widget.currentText())
                                name_field_indices[widget.currentText()] = \
                                    layer.fieldNameIndex(table.item(row, 0).text())
                            else:
                                item = table.item(row, 0).text()
                                name_fields.append(item)
                                name_field_indices[item] = layer.fieldNameIndex(item)
            return name_fields, name_field_indices

        self.node_fields, self.node_field_indices = compile_fields(self.node_layer, self.table_node_fields, 'nodes')
        self.link_fields, self.link_field_indices = compile_fields(self.link_layer, self.table_link_fields, 'links')

        for i in self.required_fields_nodes:
            if i not in self.node_fields:
                passed_checks = False
                self.error.append(i)

        for i in self.required_fields_links:
            if i not in self.link_fields:
                passed_checks = False
                self.error.append(i)

        if not passed_checks:
            self.error = '(' + ', '.join(self.error) + ')'

        return passed_checks

    def exit_procedure(self):
        self.close()

    def run_thread(self):
        QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressText( PyQt_PyObject )"), self.progress_text_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"),
                        self.progress_range_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("jobFinished( PyQt_PyObject )"), self.job_finished_from_thread)
        self.worker_thread.start()
        self.show()

    def progress_range_from_thread(self, val):
        self.progressbar.setRange(0, val)

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value)

    def progress_text_from_thread(self, value):
        self.progress_label.setText(value)

    def job_finished_from_thread(self, success):
        if not self.worker_thread.report:
            dlg2 = ReportDialog(self.iface, self.worker_thread.report)
            dlg2.show()
            dlg2.exec_()
        self.exit_procedure()