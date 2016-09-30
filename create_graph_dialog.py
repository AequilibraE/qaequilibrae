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

import numpy as np
import qgis
from PyQt4 import QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

from auxiliary_functions import *
from global_parameters import *

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms/")
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/aequilibrae/")

from create_graph_procedure import GraphCreation
from ui_Create_Graph import Ui_Create_Graph


class GraphCreationDialog(QtGui.QDialog, Ui_Create_Graph):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.validtypes = integer_types + float_types
        self.iface = iface
        self.setupUi(self)
        self.field_types = {}
        self.centroids = None
        self.progressbar0.setVisible(False)
        self.progress_label0.setVisible(False)

        self.tot_skims = 0
        self.name_skims = 0

        # FIRST, we connect slot signals
        self.links_are_bi_directional.stateChanged.connect(self.bi_directional)

        # For changing the network layer
        self.network_layer.currentIndexChanged.connect(self.load_fields_to_combo_boxes)
        # For setting centroids
        self.set_centroids_rule.stateChanged.connect(self.add_model_centroids)

        # For adding skims
        self.add_skim.clicked.connect(self.add_to_skim_list)
        self.skim_list.doubleClicked.connect(self.slot_double_clicked)

        # SECOND, we set visibility for sections that should not be shown when the form opens (overlapping items)
        #        and re-dimension the items that need re-dimensioning
        self.skim_list.setColumnWidth(0, 110)
        self.skim_list.setColumnWidth(1, 171)
        self.skim_list.setColumnWidth(2, 171)

        # Create_Network
        self.create_network.clicked.connect(self.GraphCreationPhase1)

        self.select_result.clicked.connect(
            partial(self.browse_outfile, 'Result file', self.graph_file, "Aequilibrae Graph(*.aeg)"))

        # THIRD, we load layers in the canvas to the combo-boxes
        for layer in qgis.utils.iface.legendInterface().layers():  # We iterate through all layers
            if layer.wkbType() in line_types:
                self.network_layer.addItem(layer.name())

        # loads default path from parameters
        self.path = standard_path()

    def bi_directional(self):
        if self.links_are_bi_directional.isChecked():
            self.ba_length.setVisible(True)
            self.ba_length_lbl.setVisible(True)
            self.dir_label.setVisible(True)
            self.direction_field.setVisible(True)
            self.ba_skim.setVisible(True)
            self.lblnodematch_13.setVisible(True)
        else:
            self.ba_length.setVisible(False)
            self.ba_length_lbl.setVisible(False)
            self.dir_label.setVisible(False)
            self.direction_field.setVisible(False)
            self.ba_skim.setVisible(False)
            self.lblnodematch_13.setVisible(False)

    def add_to_skim_list(self):
        try:
            layer = get_vector_layer_by_name(self.network_layer.currentText())

            ab_skim = layer.fieldNameIndex(self.ab_skim.currentText())
            ba_skim = layer.fieldNameIndex(self.ba_skim.currentText())

            if ab_skim >= 0 and ba_skim >= 0:
                self.tot_skims += 1
                self.name_skims += 1
                self.skim_list.setRowCount(self.tot_skims)
                self.skim_list.setItem(self.tot_skims - 1, 0, QtGui.QTableWidgetItem('Skim ' + str(self.name_skims)))
                self.skim_list.setItem(self.tot_skims - 1, 1,
                                       QtGui.QTableWidgetItem(self.ab_skim.currentText()))  # .encode('ascii'))
                self.skim_list.setItem(self.tot_skims - 1, 2,
                                       QtGui.QTableWidgetItem(self.ba_skim.currentText()))  # .encode('ascii'))
        except:
            qgis.utils.iface.messageBar().pushMessage("Wrong settings", "Please review the field information", level=3,
                                                      duration=3)

    def slot_double_clicked(self, mi):
        row = mi.row()
        if row > -1:
            self.skim_list.removeRow(row)
            self.tot_skims -= 1

    # GENERIC to be applied to MORE THAN ONE form
    def load_fields_to_combo_boxes(self):

        i_types = [self.direction_field, self.link_id, self.ab_skim, self.ba_skim]
        f_types = [self.ab_length, self.ba_length, self.ab_skim, self.ba_skim]

        self.field_types = {}
        for combo in i_types + f_types:
            combo.clear()
            combo.addItem('Choose Field')

        if self.network_layer.currentIndex() >= 0:
            layer = get_vector_layer_by_name(self.network_layer.currentText())
            for field in layer.dataProvider().fields().toList():
                if field.type() in integer_types:
                    self.field_types[field.name()] = field.type()
                    for combo in i_types:
                        combo.addItem(field.name())
                if field.type() in float_types:
                    self.field_types[field.name()] = field.type()
                    for combo in f_types:
                        combo.addItem(field.name())

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

    def GraphCreationPhase1(self):  # CREATING GRAPH
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
                skims = {}
                for row in range(self.tot_skims):
                    skim_name = self.skim_list.item(row, 0).text()
                    ab_field = self.layer.fieldNameIndex(self.skim_list.item(row, 1).text())

                    ba_field = -1
                    if self.links_are_bi_directional.isChecked():
                        ba_field = self.layer.fieldNameIndex(self.skim_list.item(row, 2).text())

                    abtype = self.field_types[self.skim_list.item(row, 1).text()]
                    batype = self.field_types[self.skim_list.item(row, 2).text()]

                    if abtype in ['Integer', 'integer'] and batype in ['Integer', 'integer']:
                        skims[unicode(skim_name)] = (ab_field, ba_field, np.int64)
                    else:
                        skims[unicode(skim_name)] = (ab_field, ba_field, np.float64)

                self.skims = skims

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
