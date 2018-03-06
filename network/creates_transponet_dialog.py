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
 Updated:    2017-07-18
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

        self.missing_data = -1
        self.path = standard_path()

        self.required_fields_links = ['link_id', 'a_node', 'b_node', 'direction', 'length', 'capacity_ab',
                                      'capacity_ba', 'speed_ab', 'speed_ba']
        
        self.initializable_links= {'direction': 0,
                                   'capacity_ab': self.missing_data,
                                   'capacity_ba': self.missing_data,
                                   'speed_ab': self.missing_data,
                                   'speed_ba': self.missing_data}
        self.initializable_nodes = {}
        
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

        self.table_available_link_fields.setColumnWidth(0, 150)
        self.table_link_fields.setColumnWidth(0, 120)
        self.table_link_fields.setColumnWidth(1, 60)
        self.table_link_fields.setColumnWidth(2, 130)

        self.table_available_node_field.setColumnWidth(0, 150)
        self.table_node_fields.setColumnWidth(0, 120)
        self.table_node_fields.setColumnWidth(1, 60)
        self.table_node_fields.setColumnWidth(2, 130)
        
        self.but_adds_to_links.clicked.connect(partial (self.append_to_list, 'links'))
        self.but_adds_to_nodes.clicked.connect(partial (self.append_to_list, 'nodes'))
        
        self.but_removes_from_links.clicked.connect(partial (self.removes_fields, 'links'))
        self.but_removes_from_nodes.clicked.connect(partial (self.removes_fields, 'nodes'))
    
    def removes_fields(self, layer_type):
        layer_fields, table, final_table, required_fields = self.__find_layer_changed(layer_type)

        for i in final_table.selectedRanges():
            old_fields = [final_table.item(row, 0).text() for row in xrange(i.topRow(), i.bottomRow() + 1)]
            
            for row in xrange(i.bottomRow(), i.topRow() - 1, -1):
                if final_table.item(row, 0).text() in required_fields:
                    break
                final_table.removeRow(row)
    
            counter = table.rowCount()
            for field in old_fields:
                if field not in required_fields:
                    table.setRowCount(counter + 1)
                    item1 = QTableWidgetItem(field)
                    item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    table.setItem(counter, 0, item1)
                    counter += 1
    
    def append_to_list(self, layer_type):
        layer_fields, table, final_table, required_fields = self.__find_layer_changed(layer_type)
        for i in table.selectedRanges():
            new_fields = [table.item(row,0).text() for row in xrange(i.topRow(), i.bottomRow()+1)]

            for row in xrange(i.bottomRow(), i.topRow() - 1, -1):
                table.removeRow (row)

            counter = final_table.rowCount()
            for field in new_fields:
                final_table.setRowCount(counter + 1)
                item1 = QTableWidgetItem(field)
                item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                final_table.setItem(counter, 0, item1)
    
                chb1 = QCheckBox()
                chb1.setChecked(False)
                chb1.setEnabled(False)
                chb1.stateChanged.connect(self.keep_checked)
                final_table.setCellWidget(counter, 1, self.centers_item(chb1))

                cbb = QComboBox()
                cbb.addItem(field)
                final_table.setCellWidget(counter, 2, self.centers_item(cbb))
                counter += 1
                
    def keep_checked(self):
        ch_box = self.sender()
        ch_box.setChecked(True)
            
    def __find_layer_changed(self, layer_type):
        layer_fields = None
        if layer_type == 'nodes':
            table = self.table_available_node_field
            final_table = self.table_node_fields
            # TODO : Change for the method .currentlayer()
            # Repeat the change throughout
            self.node_layer = get_vector_layer_by_name(self.node_layers_list.currentText())
            required_fields = self.required_fields_nodes
            if self.node_layer:
                layer_fields = self.node_layer.pendingFields()
        if layer_type == 'links':
            table = self.table_available_link_fields
            final_table = self.table_link_fields
            self.link_layer = get_vector_layer_by_name(self.link_layers_list.currentText())
            required_fields = self.required_fields_links
            if self.link_layer:
                layer_fields = self.link_layer.pendingFields()

        return layer_fields, table, final_table, required_fields

    def changed_layer(self, layer_type):
        try:
            layer_fields, table, final_table, required_fields = self.__find_layer_changed(layer_type)
            table.clearContents()
            table.setRowCount(0)
            # We create the comboboxes that will hold the definitions for all the fields that are mandatory for
            # creating the appropriate triggers on the SQLite file
            if layer_fields is not None:
                fields = [field.name() for field in layer_fields]
                counter = 0
                for field in fields:
                    table.setRowCount(counter + 1)
                    item1 = QTableWidgetItem(field)
                    item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    table.setItem(counter, 0, item1)
                    counter += 1
                self.counter[layer_type] = counter

            final_table.clearContents()
            final_table.setRowCount(0)

            counter = 0
            if layer_type == 'links':
                init_fields = list(self.initializable_links.keys())
            else:
                init_fields = list(self.initializable_nodes.keys())

            for rf in required_fields:
                final_table.setRowCount(counter + 1)

                item1 = QTableWidgetItem(rf)
                item1.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                final_table.setItem(counter, 0, item1)

                chb1 = QCheckBox()
                if rf in init_fields:
                    chb1.setChecked(True)
                    chb1.stateChanged.connect(partial(self.set_field_to_default, layer_type))
                else:
                    chb1.setChecked(True)
                    chb1.stateChanged.connect(partial(self.set_field_to_default, layer_type))
                    chb1.setChecked(False)
                    chb1.setEnabled(False)
                final_table.setCellWidget(counter, 1, self.centers_item(chb1))
                counter += 1
        except:
            pass

    def centers_item(self, item):
        cell_widget = QWidget()
        lay_out = QHBoxLayout(cell_widget)
        lay_out.addWidget(item)
        lay_out.setAlignment(Qt.AlignCenter)
        lay_out.setContentsMargins(0, 0, 0, 0)
        cell_widget.setLayout(lay_out)
        return cell_widget
    
    def set_field_to_default(self, layer_type):
        layer_fields, table, final_table, required_fields = self.__find_layer_changed(layer_type)
        
        if layer_fields is not None:
            ch_box = self.sender()
            parent = ch_box.parent()
            for i in range(final_table.rowCount()):
                if final_table.cellWidget(i, 1) is parent:
                    row = i
                    break
    
            if ch_box.isChecked():
                final_table.setCellWidget(row, 2, QWidget())
            else:
                cbb = QComboBox()
                for i in layer_fields:
                    cbb.addItem(i.name())
                final_table.setCellWidget(row, 2, self.centers_item(cbb))

    def create_net(self):
        self.assembles_data()
        self.output_file, file_type = GetOutputFileName(self, 'TranspoNet', ["SQLite(*.sqlite)"], ".sqlite",
                                                        self.path)
        
        parameters = [self.output_file,
                      self.node_layer,
                      self.node_fields,
                      self.required_fields_nodes,
                      self.initializable_nodes,
                      self.link_layer,
                      self.link_fields,
                      self.required_fields_links,
                      self.initializable_links]

        self.but_create_network_file.setVisible(False)
        self.progressbar.setVisible(True)
        self.progress_label.setVisible(True)
        self.worker_thread = CreatesTranspoNetProcedure(qgis.utils.iface.mainWindow(), *parameters)
        self.run_thread()

    def assembles_data(self):
        def compile_fields(layer, table):
            fields = {}
            for row in range(table.rowCount()):
                f = table.item(row, 0).text()
                if table.cellWidget(row, 1).findChildren(QCheckBox)[0].isChecked():
                    val = -1
                else:
                    widget = table.cellWidget(row, 2).findChildren(QComboBox)[0]
                    source_name = widget.currentText()
                    val = layer.fieldNameIndex(source_name)
                fields[f] = val
                        
            return fields

        self.node_fields = compile_fields(self.node_layer, self.table_node_fields)
        self.link_fields = compile_fields(self.link_layer, self.table_link_fields)

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
        if self.worker_thread.report:
            dlg2 = ReportDialog(self.iface, self.worker_thread.report)
            dlg2.show()
            dlg2.exec_()
        self.exit_procedure()