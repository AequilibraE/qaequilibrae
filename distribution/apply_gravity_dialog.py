"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Trip distribution model application
 Purpose:    Loads GUI to apply gravity model

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-10-03
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
import qgis
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtGui, QtCore
import sys
import os
from functools import partial
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")) + "//forms//")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__),"..")))

from auxiliary_functions import *
from load_matrix_dialog import LoadMatrixDialog
from load_vector_dialog import LoadVectorDialog
from report_dialog import ReportDialog

from apply_gravity_procedure import ApplyGravityProcedure
from ui_apply_gravity import Ui_apply_gravity
from load_distribution_model import LoadDistributionModelDialog
import yaml


try:
    import omx
    OMX = True
except:
    OMX = False

class ApplyGravityDialog(QDialog, Ui_apply_gravity):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()

        self.error = None
        self.outname = None
        self.output = None
        self.report = None

        self.rows = None
        self.columns = None
        self.impedance = None
        self.model = None

        self.error_icon = os.path.abspath(os.path.join(os.path.dirname(__file__),"..")) + "//icons//error.png"
        self.error_pic = pic = QtGui.QPixmap(self.error_icon)

        self.loaded_icon = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) + "//icons//check_mark.png"
        self.loaded_pic = pic = QtGui.QPixmap(self.loaded_icon)


        self.lbl_prod.setPixmap(self.error_pic)
        self.lbl_atra.setPixmap(self.error_pic)
        self.lbl_imped.setPixmap(self.error_pic)
        self.lbl_par.setPixmap(self.error_pic)
        self.lbl_output.setPixmap(self.error_pic)


        self.radio_friction.setEnabled(False)

        # Hide the progress bars
        self.progressbar.setVisible(False)
        self.progressbar.setValue(0)

        # Connect slot signals
        self.but_load_rows.clicked.connect(partial(self.find_vectors, 'rows'))
        self.but_load_columns.clicked.connect(partial(self.find_vectors, 'columns'))
        self.but_load_impedance.clicked.connect(self.find_matrices)

        self.but_select_model_file.clicked.connect(self.get_model_file)
        self.but_manual_input.clicked.connect(self.manual_model_input)

        self.but_select_output.clicked.connect(self.browse_outfile)

        self.but_apply_gravity.clicked.connect(self.run)

    def get_model_file(self):
        file_types = "Model File(*.yaml)"
        model_file = QFileDialog.getOpenFileName(None, 'Distribution model', self.path, file_types)
        if len(model_file) > 0:
            with open(model_file, 'r') as yml:
                self.model = yaml.safe_load(yml)

            dlg2 = LoadDistributionModelDialog(self.iface, self.model['function'], self.model['parameters'])
            dlg2.show()
            dlg2.exec_()

            self.model = dlg2.model
            self.lbl_par.setPixmap(self.loaded_pic)

            if self.model['function'].upper() == 'EXPO':
                self.radio_expo.setChecked(True)

            if self.model['function'].upper() == 'GAMMA':
                self.radio_gamma.setChecked(True)

            if self.model['function'].upper() == 'POWER':
                self.radio_power.setChecked(True)

            if self.model['function'].upper() == 'FRICTION':
                self.radio_friction.setChecked(True)

    def manual_model_input(self):
        if self.radio_expo.isChecked():
            func = 'EXPO'

        if self.radio_gamma.isChecked():
            func = 'GAMMA'

        if self.radio_power.isChecked():
            func = 'POWER'

        if self.radio_friction.isChecked():
            func = 'FRICTION'

        dlg2 = LoadDistributionModelDialog(self.iface, func, {})
        dlg2.show()
        dlg2.exec_()

        self.model = dlg2.model
        self.lbl_par.setPixmap(self.loaded_pic)

    def browse_outfile(self):
        file_types = "Comma-separated files(*.csv);;Numpy Binnary Array(*.npy)"
        if OMX:
            file_types += ";;OpenMatrix(*.omx)"
        new_name = QFileDialog.getSaveFileName(None, 'Result matrix', self.path, file_types)
        if new_name is not None:
            self.outname = new_name
            self.report_output.setText(new_name)
            self.lbl_output.setPixmap(self.loaded_pic)

    def run_thread(self):
        # QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        # QObject.connect(self.worker_thread, SIGNAL("ProgressText( PyQt_PyObject )"), self.progress_text_from_thread)
        # QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.progress_range_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),
                        self.job_finished_from_thread)
        self.worker_thread.start()
        self.exec_()

    def find_matrices(self):
        dlg2 = LoadMatrixDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        if dlg2.matrix is not None:
            self.impedance = dlg2.matrix
            self.report_matrix.setText('Matrix: LOADED')
            a = "{:6,.0f}".format(self.impedance.shape[0])
            b = "{:6,.0f}".format(self.impedance.shape[1])
            self.report_matrix.append('Dimensions: '+ a + ' X ' + b)
            self.lbl_imped.setPixmap(self.loaded_pic)

    def find_vectors(self, destination):
        dlg2 = LoadVectorDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        if dlg2.vector is not None:
            text = ['Vector Loaded']
            a = "Zones: " + "{:6,.0f}".format(dlg2.vector.shape[0])
            text.append(a)
            a = "Total Demand: " + "{:10,.4f}".format(np.sum(dlg2.vector))
            text.append(a)

            if destination == 'rows':
                self.rows = dlg2.vector
                self.report_prod.setText(text[0])
                self.report_prod.append(text[1])
                self.report_prod.append(text[2])
                self.lbl_prod.setPixmap(self.loaded_pic)
            else:
                self.columns = dlg2.vector
                self.report_atra.setText(text[0])
                self.report_atra.append(text[1])
                self.report_atra.append(text[2])
                self.lbl_atra.setPixmap(self.loaded_pic)

    # def progress_range_from_thread(self, val):
    #     self.progressbar.setRange(0, val[1])
    #
    # def progress_value_from_thread(self, value):
    #     self.progressbar.setValue(value[1])
    #
    # def progress_text_from_thread(self, value):
    #     self.progress_label.setText(value[1])

    def job_finished_from_thread(self, success):
        if self.worker_thread.error is not None:
            qgis.utils.iface.messageBar().pushMessage("Procedure error: ", self.worker_thread.error, level=3)
        else:
            self.output = self.worker_thread.gravity.output
            self.report = self.worker_thread.gravity.report

            if self.outname[-3:].upper() == 'NPY':
                np.save(self.outname, self.output)

            else:
                outp = open(self.outname, 'w')
                print >> outp, 'O,D,Flow'
                print_zeros = get_parameter_chain(['system', 'report zeros'])
                if print_zeros:
                    for i in range(self.output.shape[0]):
                        for j in range(self.output.shape[1]):
                            print >> outp, str(i) + ',' + str(j) + ',' + str(self.output[i, j])
                else:
                    for i in range(self.output.shape[0]):
                        for j in range(self.output.shape[1]):
                            if self.output[i, j]:
                                print >> outp, str(i) + ',' + str(j) + ',' + str(self.output[i, j])
                    outp.flush()
                    outp.close()
        self.exit_procedure()

    def run(self):
        if self.check_data():
            self.worker_thread = ApplyGravityProcedure(qgis.utils.iface.mainWindow(), self.impedance, self.rows,
                                                       self.columns, self.model)
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Input error", self.error, level=3)

    def check_data(self):
        if self.impedance is None:
            self.error = 'Impedance missing'

        if self.rows is None:
            self.error = 'Production/Origins vector missing'

        if self.columns is None:
            self.error = 'Attractions/Destinations vector missing'

        if self.model is None:
            self.error = 'Model specification is missing'

        if self.outname is None:
            self.error = 'Parameters for output missing'

        if self.error is not None:
            return False
        else:
            return True

    def exit_procedure(self):
        self.close()
        dlg2 = ReportDialog(self.iface, self.report)
        dlg2.show()
        dlg2.exec_()



