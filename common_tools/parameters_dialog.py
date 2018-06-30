"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Main interface for changing the algorithm parameters
 Purpose:    changing algorithm parameters

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-08-15
 Updated:    2016-10-03
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import qgis
from qgis.core import *

# from PyQt4.QtGui import *
# from PyQt4.Qsci import QsciLexerYAML
# from PyQt4 import uic

from qgis.PyQt.Qsci import QsciLexerYAML
from qgis.PyQt.QtGui import *
from qgis.PyQt import QtWidgets, uic

import os
import yaml

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),  'forms/ui_parameters.ui'))

class ParameterDialog(QtWidgets.QDialog, FORM_CLASS):
    # def __init__(self, iface):
    def __init__(self, iface, parent=None):
        super(ParameterDialog, self).__init__(parent)
        # QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.path = os.path.dirname(os.path.dirname(__file__)) + "/aequilibrae/"
        self.default_values = None
        self.parameter_values = None
        self.current_data = None
        self.error = False
        # Configures the text editor
        font = QFont()
        font.setFamily('Courier')
        font.setFixedPitch(True)
        font.setPointSize(12)
        lexer = QsciLexerYAML()
        lexer.setDefaultFont(font)
        self.text_box.setLexer(lexer)

        # Load the data
        self.load_original_data()
        self.load_defaults()

        # Connect all buttons
        self.but_validate.clicked.connect(self.validate_data)
        self.but_save.clicked.connect(self.save_new_parameters)
        self.but_defaults.clicked.connect(self.load_default_data)
        self.but_close.clicked.connect(self.exit_procedure)

    # Load the current parameters onto the GUI
    def load_original_data(self):
        with open(self.path + 'parameters.yml', 'r') as yml:
            self.parameter_values = yaml.safe_load(yml)
        pretty_data = yaml.dump(self.parameter_values, default_flow_style=False)
        self.text_box.setText(str(pretty_data))

    # Read defaults to memory
    def load_defaults(self):
        with open(self.path + 'parameter_default.yml', 'r') as yml:
            self.default_values = yaml.safe_load(yml)

    def validate_data(self):
        self.error = False
        self.current_data = yaml.safe_load(self.text_box.text())
        if isinstance(self.current_data, dict):  # Checking if we did not erase everything
            self.compare_dictionaries(self.default_values, self.current_data)
        else:
            self.error = True

        if self.error:
            self.but_save.setEnabled(False)
            self.iface.messageBar().pushMessage("Error", "Parameter structure was compromised. Please reset "
                                                               "to defaults", level=3, duration=10)
            # qgis.utils.iface.messageBar().pushMessage("Error", "Parameter structure was compromised. Please reset "
            #                                                    "to defaults", level=3, duration=10)
        else:
            self.but_save.setEnabled(True)

    def compare_dictionaries(self, dict1, dict2):
        try:
            # Check if we did not delete a key
            for key in dict1:
                if key not in dict2:
                    self.error = True
                    break
                if type(dict1[key]) != type(dict2[key]):
                    self.error = True
                    break
                if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                    self.compare_dictionaries(dict1[key], dict2[key])

            # Check if we did not add a key
            for key in dict2:
                if key not in dict1:
                    self.error = True
                    break
        except:
            self.error = True

    def save_new_parameters(self):
        self.validate_data()
        if not self.error:
            stream = open(self.path + '/parameters.yml', 'w')
            yaml.dump(self.current_data, stream, default_flow_style=False)
            stream.close()
            self.but_close.setText('Close')

    def load_default_data(self):
        pretty_data = yaml.dump(self.default_values, default_flow_style=False)
        self.text_box.setText(str(pretty_data))
        self.error = False

    def exit_procedure(self):
        self.close()
