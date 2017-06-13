"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Loading distribution model parameters
 Purpose:    Loads GUI for loading distribution model parameters

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
import os
from PyQt4 import QtGui, uic
from PyQt4.QtGui import *


from ..common_tools.auxiliary_functions import *

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'forms/ui_gravity_parameters.ui'))


class LoadDistributionModelDialog(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, function, parameters=None):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()
        self.model = None

        self.function = function
        if 'alpha' in parameters:
            self.alpha_box.setPlainText(str(parameters['alpha']))

        if 'beta' in parameters:
            self.beta_box.setPlainText(str(parameters['beta']))

        if function.upper() == 'EXPO':
            self.alpha_box.setEnabled(False)
            self.alpha_box.setPlainText('')

        if function.upper() == 'POWER':
            self.beta_box.setEnabled(False)
            self.beta_box.setPlainText('')

        # For adding skims
        self.but_done.clicked.connect(self.return_model)

    def return_model(self):  # CREATING GRAPH
        par = {}
        if len(self.alpha_box.toPlainText()) > 0:
            par['alpha'] = float(self.alpha_box.toPlainText())

        if len(self.beta_box.toPlainText()) > 0:
            par['beta'] = float(self.beta_box.toPlainText())

        self.model = {'function': self.function,
                      'parameters': par}
        self.close()
