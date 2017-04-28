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
 Updated:    
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import qgis
from qgis.core import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
from auxiliary_functions import *
import sys
from qgis.gui import QgsMapLayerProxyModel
from pyspatialite import dbapi2 as db
import os
from global_parameters import *
from functools import partial
from get_output_file_name import GetOutputFileName

sys.modules['qgsmaplayercombobox'] = qgis.gui
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                            'forms/ui_transponet_construction.ui'))

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

        self.node_layers_list.layerChanged.connect(partial (self.changed_layer, 'nodes'))
        self.node_layers_list.setFilters(QgsMapLayerProxyModel.PointLayer)

        self.link_layers_list.layerChanged.connect(partial (self.changed_layer, 'links'))
        self.link_layers_list.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.node_fields = []
        self.link_fields = []
        self.node_field_indices = {}
        self.link_field_indices = {}

        self.changed_layer('nodes')
        self.changed_layer('links')

    def changed_layer(self, layer_type):
        if layer_type == 'nodes':
            table = self.table_node_fields
            self.node_layer = get_vector_layer_by_name(self.node_layers_list.currentText())
            layer_fields = self.node_layer.pendingFields()
        else:
            table = self.table_link_fields
            self.link_layer = get_vector_layer_by_name(self.link_layers_list.currentText())
            layer_fields = self.link_layer.pendingFields()

        # We create the comboboxes that will hold the definitions for all the fields that are mandatory for
        # creating the appropriate triggers on the SQLite file
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
            item = QTableWidgetItem(field)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(counter, 0, item)

            item = QTableWidgetItem(field)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            table.setItem(counter, 2, item)

            q = QCheckBox()
            q.stateChanged.connect(partial(self.set_field_to_default, layer_type))

            table.setCellWidget(counter, 1, centers_item(q))

            q = QCheckBox()
            q.setChecked(True)
            q.stateChanged.connect(partial(self.set_field_to_keep, layer_type))
            table.setCellWidget(counter, 3, centers_item(q))
            counter += 1

        self.counter[layer_type] = counter


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

            q = QComboBox()
            for i in required_fields:
                q.addItem(i)

            table.setCellWidget(row, 2, centers_item(q))


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
            nfields = ", ".join(self.node_fields)
            lfields = ", ".join(self.link_fields)

            self.output_file, file_type = GetOutputFileName(self, 'TranspoNet', ["SQLite(*.sqlite)"], ".sqlite", self.path)
            self.run_series_of_queries(os.path.join(os.path.dirname(os.path.abspath(__file__)),'queries_for_empty_file.sql'))

            conn = db.connect(self.output_file)
            curr = conn.cursor()

            # We add the node layer
            for f in self.node_layer.getFeatures():
                attrs = []
                for q in self.node_fields:
                    attrs.append(str(f.attributes()[self.node_field_indices[q]]))
                attrs = ', '.join(attrs)
                sql = 'INSERT INTO nodes (' + nfields + ', geometry) '
                sql += "VALUES (" + attrs + ", "
                sql += "GeomFromText('" + f.geometry().exportToWkt().upper() + "', " + str(self.node_layer.crs().authid().split(":")[1]) + "))"
                print sql
                a = curr.execute(sql)
            conn.commit()
            # DONE
            self.run_series_of_queries(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'triggers.sql'))

    def consistency_checks(self):
        passed_checks = True
        def compile_fields(layer, table, link_type):
            name_fields = []
            name_field_indices = {}
            for row in range(self.counter[link_type]):
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
                break

        for i in self.required_fields_links:
            if i not in self.link_fields:
                passed_checks = False
                break
        return passed_checks

    def run_series_of_queries(self, queries):

        conn = db.connect(self.output_file)
        curr = conn.cursor()
        # Reads all commands
        sql_file = open(queries, 'r')
        query_list = sql_file.read()
        sql_file.close()
        # Split individual commands
        sql_commands_list = query_list.split('#')
        # Run one query/command at a time
        for cmd in sql_commands_list:
            print cmd
            try:
                curr.execute(cmd)
            except:
                print cmd
        conn.commit()
        conn.close()
    def exit_procedure(self):
        self.close()