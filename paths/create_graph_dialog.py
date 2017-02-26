"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Creating the graph from geographic layer
 Purpose:    GUI for creating the graph

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-07-30
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import sys
from functools import partial

import os
import numpy as np
import qgis
from PyQt4 import QtGui, uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

from auxiliary_functions import *
from global_parameters import *
from create_graph_procedure import GraphCreation
from graph_advanced_features import GraphAdvancedFeatures

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/forms/", 'Ui_Create_Graph.ui'))


class GraphCreationDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.validtypes = integer_types + float_types
        self.iface = iface
        self.setupUi(self)
        self.centroids = None
        self.block_through_centroids = False
        self.selected_only = False

        self.progressbar0.setVisible(False)
        self.progress_label0.setVisible(False)
        self.fields = 0
        self.fields_lst.setColumnWidth(0, 180)
        self.fields_lst.setColumnWidth(1, 180)
        self.fields_lst.setColumnWidth(2, 40)
        self.fields_lst.setColumnWidth(3, 60)

        # FIRST, we connect slot signals
        self.links_are_bi_directional.stateChanged.connect(self.bi_directional)
        self.chk_dual_fields.stateChanged.connect(self.dual_fields)

        # For changing the network layer
        self.network_layer.currentIndexChanged.connect(self.load_fields_to_combo_boxes)

        # Calls the advanced features
        self.but_advanced.clicked.connect(self.call_advanced_features)

        # # for changing the skim field
        # self.ab_skim.currentIndexChanged.connect(partial(self.choose_a_field, 'AB'))
        # self.ba_skim.currentIndexChanged.connect(partial(self.choose_a_field, 'BA'))
        #
        # # For setting centroids
        # self.set_centroids_rule.stateChanged.connect(self.add_model_centroids)
        #
        # # Create_Network
        # self.create_network.clicked.connect(self.run_graph_creation)
        #
        # self.select_result.clicked.connect(
        #     partial(self.browse_outfile, 'Result file', self.graph_file, "Aequilibrae Graph(*.aeg)"))

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.legendInterface().layers():  # We iterate through all layers
            if layer.wkbType() in line_types:
                self.network_layer.addItem(layer.name())

        # loads default path from parameters
        self.path = standard_path()
        #
        # #set initial values for skim list
        # self.set_initial_value_if_available()
        self.dual_fields()
        self.bi_directional()



    def bi_directional(self):
        if self.links_are_bi_directional.isChecked():
            self.chk_dual_fields.setVisible(True)
            self.dir_label.setVisible(True)
            self.direction_field.setVisible(True)
            self.fields_lst.setColumnWidth(1, 180)
            self.fields_lst.horizontalHeaderItem(0).setText("AB field")
            self.fields_lst.setGeometry(QRect(10, 130, 511, 261))
        else:
            self.chk_dual_fields.setVisible(True)
            self.dir_label.setVisible(False)
            self.direction_field.setVisible(False)
            self.fields_lst.setColumnWidth(1, 0)
            self.fields_lst.horizontalHeaderItem(0).setText("Link field")
            self.fields_lst.setGeometry(QRect(10, 130, 331, 261))
        self.dual_fields()

    def dual_fields(self):
        if self.chk_dual_fields.isChecked():
            self.fields_lst.setColumnWidth(1, 0)
            self.fields_lst.horizontalHeaderItem(0).setText("Fields *")
            self.fields_lst.setGeometry(QRect(10, 130, 331, 261))
        else:
            self.fields_lst.setColumnWidth(1, 180)
            self.fields_lst.horizontalHeaderItem(0).setText("AB field")
            self.fields_lst.setGeometry(QRect(10, 130, 511, 261))
        self.list_all_fields()

    def set_initial_value_if_available(self):
        all_items = [self.ab_skim.itemText(i) for i in range(self.ab_skim.count())]

        for i in all_items:
            if 'AB' in i:
                index = self.ab_skim.findText(i, Qt.MatchFixedString)
                if index >= 0:
                    self.ab_skim.setCurrentIndex(index)
                break

    # GENERIC to be applied to MORE THAN ONE form
    def load_fields_to_combo_boxes(self):
        i_types = [self.direction_field, self.link_id]

        for combo in i_types:
            combo.clear()

        if self.network_layer.currentIndex() >= 0:
            self.layer = get_vector_layer_by_name(self.network_layer.currentText())
            for field in self.layer.pendingFields().toList():
                if field not in reserved_fields:
                    if field.type() in integer_types:
                        for combo in i_types:
                            combo.addItem(field.name())
        self.list_all_fields()

    def list_all_fields(self):
        self.fields_lst.setRowCount(0)
        self.fields = 0

        def add_new_field_to_list(text, sec_field):
            self.fields_lst.setRowCount(self.fields + 1)
            self.fields_lst.setItem(self.fields, 0, QTableWidgetItem(text))

            def centralized_widget(widget):
                my_widget = QWidget()
                #chk_bx.setCheckState(Qt.Checked) # If we wanted them all checked by default
                lay_out = QHBoxLayout(my_widget)
                lay_out.addWidget(widget)
                lay_out.setAlignment(Qt.AlignCenter)
                lay_out.setContentsMargins(0, 0, 0, 0)
                my_widget.setLayout(lay_out)
                return my_widget

            chk = centralized_widget(QCheckBox())
            q = QRadioButton()
            q.toggled.connect(self.handleItemClicked)
            chk2 = centralized_widget(q)


            self.fields_lst.setCellWidget(self.fields, 2, chk)
            self.fields_lst.setCellWidget(self.fields, 3, chk2)

            if sec_field is not None:
                cmb_bx = centralized_widget(sec_field)
                self.fields_lst.setCellWidget(self.fields, 1, cmb_bx)

            self.fields += 1

        if self.network_layer.currentIndex() >= 0:

            layer = get_vector_layer_by_name(self.network_layer.currentText())
            all_fields = layer.pendingFields().toList()
            fields = []
            for field in all_fields:
                if field.type() in integer_types + float_types:
                    fields.append(field.name())
            fields = [x.lower() for x in fields]
            for f in reserved_fields:
                if f in fields:
                    fields.pop(f)

            if self.chk_dual_fields.isChecked():
                for field in fields:
                    if '_ab' in field:
                        if field.replace('_ab', '_ba') in fields:
                            fields.remove(field.replace('_ab', '_ba'))
                            field = field.replace('_ab', '_*')
                            add_new_field_to_list(field, None)
                    elif '_ba' in field:
                        if field.replace('_ba', '_ab') in fields:
                            fields.remove(field.replace('_ba', '_ab'))
                            field = field.replace('_ba', '_*')
                            add_new_field_to_list(field, None)
                    else:
                        add_new_field_to_list(field, None)
            else:
                for field in fields:
                    cmb_bx = QComboBox()
                    for f in fields:
                        cmb_bx.addItem(f)
                    cmb_bx.setCurrentIndex(cmb_bx.findText(field, Qt.MatchFixedString))
                    add_new_field_to_list(field, cmb_bx)

    def handleItemClicked(self):
        box = self.sender()
        parent = box.parent()

        for i in range(self.fields):
            if self.fields_lst.cellWidget(i, 3) is parent:
                row = i
                break

        for i in range(self.fields):
            if i != row:
                for chk in self.fields_lst.cellWidget(i, 3).findChildren(QRadioButton):
                    chk.setChecked(False)

    def call_advanced_features(self):
        dlg2 = GraphAdvancedFeatures(self.iface)
        dlg2.show()
        dlg2.exec_()
        self.centroids = dlg2.centroids
        self.block_through_centroids = dlg2.block_through_centroids
        self.selected_only = dlg2.selected_only



    def add_model_centroids(self):
        self.model_centroids.setEnabled(False)
        if self.set_centroids_rule.isChecked():
            self.model_centroids.setEnabled(True)

    def run_thread(self):

        QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressText( PyQt_PyObject )"), self.progress_text_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"),
                        self.progress_range_from_thread)

        QObject.connect(self.worker_thread, SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),
                        self.finished_threaded_procedure)

        self.worker_thread.start()
        self.exec_()

    # VAL and VALUE have the following structure: (bar/text ID, value)
    def progress_range_from_thread(self, val):
        self.progressbar0.setRange(0, val)

    def progress_value_from_thread(self, val):
        self.progressbar0.setValue(val)

    def progress_text_from_thread(self, val):
        self.progress_label0.setText(val)

    def finished_threaded_procedure(self, param):
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Input data not provided correctly", self.worker_thread.error,
                                                      level=1)
        else:
            bcf = False
            if self.path_through_connectors.isChecked():
                bcf = True

            if self.centroids is None:
                self.worker_thread.graph.set_graph(cost_field='length', skim_fields=list(self.skims.keys()),
                                                   block_centroid_flows=bcf)
            else:
                self.worker_thread.graph.set_graph(centroids=int(self.centroids), cost_field='length',
                                                   skim_fields=list(self.skims.keys()), block_centroid_flows=bcf)

            self.worker_thread.graph.save_to_disk(self.output)
            qgis.utils.iface.messageBar().pushMessage("Finished. ", 'Graph saved successfully', level=3)
            self.exit_procedure()

    def browse_outfile(self, dialogbox_name, outbox, file_types):
        if len(outbox.text()) == 0:
            new_name = QFileDialog.getSaveFileName(None, dialogbox_name, self.path, file_types)
        else:
            new_name = QFileDialog.getSaveFileName(None, dialogbox_name, outbox.text(), file_types)
        if new_name is not None:
            outbox.setText(new_name)

    def run_graph_creation(self):  # CREATING GRAPH
        self.error = None
        text = ''

        self.layer = get_vector_layer_by_name(self.network_layer.currentText())

        if self.layer is None:
            self.error = 'Link layer not selected'
        else:
            self.linkid = self.layer.fieldNameIndex(self.link_id.currentText())

            if self.linkid < 0:
                text = 'ID Field not provided\n'

            # Indices for the fields with time
            self.ab_length = self.layer.fieldNameIndex(self.ab_length.currentText())
            if self.ab_length < 0:
                text = text + 'AB length field not selected\n'

            self.bidirectional = False
            self.directionfield = None
            if self.links_are_bi_directional.isChecked():
                self.bidirectional = True
                self.directionfield = self.layer.fieldNameIndex(self.direction_field.currentText())
                if self.directionfield < 0:
                    text = text + 'Direction field not selected\n'

                self.ba_length = self.layer.fieldNameIndex(self.ba_length.currentText())
                if self.ba_length < 0:
                    text = text + 'BA length field not selected\n'
            else:
                self.ba_length = False
            if text != '':
                self.error = text

            if self.error is None:
                a = self.layer.fieldNameIndex("A_NODE")
                b = self.layer.fieldNameIndex("B_NODE")
                if a < 0:
                    text = 'No A_NODE field\n'
                if b < 0:
                    text = text + 'No B_NODE field'
                if text != '':
                    self.error = text
        if self.error is None:
            if self.set_centroids_rule.isChecked():
                centroids = self.model_centroids.text()
                if centroids.isdigit():
                    self.centroids = centroids
                else:
                    self.error = 'value of centroids is not numeric'
            else:
                self.centroids = None


                # Identify the skim fields
        if self.error is None:
            self.skims = {}
            if self.tot_skims > 0:
                i = []  # check all skim_names
                for row in range(self.tot_skims):
                    skim_name = self.skim_list.item(row, 0).text()
                    if skim_name in i:
                        self.error = "There is a duplicated skim_name"
                    if skim_name == "":
                        self.error = "There is a skim with no name"
                    i.append(skim_name)

                # check all field names
                for row in range(self.tot_skims):
                    i = self.layer.fieldNameIndex(self.skim_list.item(row, 1).text())
                    if i < 0:
                        self.error = "There is a skim with the wrong AB field: " + self.skim_list.item(row, 1).text()
                    if self.links_are_bi_directional.isChecked():
                        i = self.layer.fieldNameIndex(self.skim_list.item(row, 2).text())
                        if i < 0:
                            self.error = "There is a skim with the wrong BA field: " + self.skim_list.item(row,
                                                                                                           2).text()

        self.output = self.graph_file.text()
        if self.error == None and self.output == "":
            self.error = 'No file name was provided for the graph'

        if self.error == None:
            if self.use_link_selection.isChecked():
                self.selected_only = True
                self.featcount = self.layer.selectedFeatureCount()
            else:
                self.selected_only = False
                self.featcount = self.layer.featureCount()

            self.progressbar0.setVisible(True)
            self.progress_label0.setVisible(True)
            self.Tabs.setCurrentIndex(2)

            self.lbl_funding1.setVisible(False)
            self.lbl_funding2.setVisible(False)

            self.worker_thread = GraphCreation(qgis.utils.iface.mainWindow(), self.layer, self.linkid, self.ab_length,
                                               self.bidirectional, self.directionfield, self.ba_length, self.skims,
                                               self.selected_only, self.featcount)
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Input data not provided correctly", self.error, level=3)

    def exit_procedure(self):
        self.close()
