"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Trip distribution model calibration
 Purpose:    Loads GUI to calibrate gravity model

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-10-23
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtGui, uic
from functools import partial
import numpy as np
import os


from ..common_tools import LoadMatrixDialog
from ..common_tools.auxiliary_functions import *
from ..common_tools import ReportDialog


from calibrate_gravity_procedure import CalibrateGravityProcedure
import yaml
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'forms/ui_gravity_calibration.ui'))



class CalibrateGravityDialog(QDialog, FORM_CLASS):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()

        self.error = None
        self.report = None

        self.observed = None
        self.impedance = None
        self.function = None
        self.result_file = None

        self.error_icon = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) + "//icons//error.png"
        self.error_pic = pic = QtGui.QPixmap(self.error_icon)
        self.loaded_icon = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) + "//icons//check_mark.png"
        self.loaded_pic = pic = QtGui.QPixmap(self.loaded_icon)

        self.lbl_observed.setPixmap(self.error_pic)
        self.lbl_imped.setPixmap(self.error_pic)
        self.lbl_par.setPixmap(self.error_pic)
        self.lbl_output.setPixmap(self.error_pic)

        self.radio_friction.setEnabled(False)
        self.radio_gamma.setEnabled(False)

        # Hide the progress bars
        self.progressbar.setVisible(False)
        self.progressbar.setValue(0)

        # Connect slot signals
        self.but_load_observed.clicked.connect(partial(self.find_matrices, 'observed'))
        self.but_load_impedance.clicked.connect(partial(self.find_matrices, 'impedance'))

        self.radio_expo.clicked.connect(self.model_spec)
        self.radio_gamma.clicked.connect(self.model_spec)
        self.radio_power.clicked.connect(self.model_spec)
        self.radio_friction.clicked.connect(self.model_spec)

        self.but_select_output.clicked.connect(self.browse_outfile)
        self.but_calibrate_gravity.clicked.connect(self.run)

    def model_spec(self):
        if self.radio_expo.isChecked():
            self.function = 'EXPO'

        if self.radio_gamma.isChecked():
            self.function = 'GAMMA'

        if self.radio_power.isChecked():
            self.function = 'POWER'

        if self.radio_friction.isChecked():
            self.function = 'FRICTION'

        self.lbl_par.setPixmap(self.loaded_pic)

    def browse_outfile(self):
        file_types = "Model specification(*.yaml)"
        new_name = QFileDialog.getSaveFileName(None, 'Model file', self.path, file_types)

        if new_name:
            if new_name[-4:].upper() != 'YAML':
                new_name = new_name + '.yaml'
            self.result_file = new_name
            self.report_output.setText(new_name)
            self.lbl_output.setPixmap(self.loaded_pic)
        else:
            self.lbl_output.setPixmap(self.error_pic)
            self.result_file = None


    def run_thread(self):
        # QObject.connect(self.worker_thread, SIGNAL("ProgressValue( PyQt_PyObject )"), self.progress_value_from_thread)
        # QObject.connect(self.worker_thread, SIGNAL("ProgressText( PyQt_PyObject )"), self.progress_text_from_thread)
        # QObject.connect(self.worker_thread, SIGNAL("ProgressMaxValue( PyQt_PyObject )"), self.progress_range_from_thread)
        QObject.connect(self.worker_thread, SIGNAL("finished_threaded_procedure( PyQt_PyObject )"),
                        self.job_finished_from_thread)
        self.worker_thread.start()
        self.exec_()

    def find_matrices(self, item):
        dlg2 = LoadMatrixDialog(self.iface)
        dlg2.show()
        dlg2.exec_()
        if dlg2.matrix is not None:
            a = "{:6,.0f}".format(dlg2.matrix.shape[0])
            b = "{:6,.0f}".format(dlg2.matrix.shape[1])
            if item == 'impedance':
                self.impedance = dlg2.matrix
                self.report_impedance.setText('Matrix: LOADED')
                self.report_impedance.append('Dimensions: ' + a + ' X ' + b)
                self.lbl_imped.setPixmap(self.loaded_pic)
            else:
                d = "{:10,.0f}".format(np.sum(dlg2.matrix))
                self.observed = dlg2.matrix
                self.report_observed.setText('Matrix: LOADED')
                self.report_observed.append('Dimensions: ' + a + ' X ' + b)
                self.report_observed.append('Total demand: ' + d)
                self.lbl_observed.setPixmap(self.loaded_pic)

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
            self.report = self.worker_thread.gravity.report
            stream = open(self.result_file, 'w')
            yaml.dump(self.worker_thread.gravity.model, stream, default_flow_style=False)
            stream.close()

        self.exit_procedure()

    def run(self):
        if self.check_data():
            self.worker_thread = CalibrateGravityProcedure(qgis.utils.iface.mainWindow(), self.observed, self.impedance,
                                                           self.function)
            self.run_thread()
        else:
            qgis.utils.iface.messageBar().pushMessage("Input error", self.error, level=3)

    def check_data(self):
        if self.impedance is None:
            self.error = 'Impedance missing'

        if self.result_file is None:
            self.error = 'Parameters for output missing'

        if self.error is not None:
            return False
        else:
            return True

    def exit_procedure(self):
        self.close()
        if self.report is not None:
            dlg2 = ReportDialog(self.iface, self.report)
            dlg2.show()
            dlg2.exec_()
