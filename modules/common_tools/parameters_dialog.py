import logging
import os
from os.path import join, isfile

import yaml

from aequilibrae.parameters import Parameters
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.Qsci import QsciLexerYAML
from qgis.PyQt.QtGui import QFont

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_parameters.ui"))


class ParameterDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project, parent=None):
        super(ParameterDialog, self).__init__(parent)
        # QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.setupUi(self)

        self.p = Parameters()
        self.path = self.p.file

        self.default_values = self.p._default
        self.parameter_values = self.p.parameters
        self.current_data = None
        self.error = False
        # Configures the text editor
        font = QFont()
        font.setFamily("Courier")
        font.setFixedPitch(True)
        font.setPointSize(12)
        lexer = QsciLexerYAML()
        lexer.setDefaultFont(font)
        self.text_box.setLexer(lexer)
        self.text_box.setFolding(self.text_box.PlainFoldStyle)
        self.logger = logging.getLogger("AequilibraEGUI")

        # Load the data
        self.load_original_data()

        # Connect all buttons
        self.but_validate.clicked.connect(self.validate_data)
        self.but_save.clicked.connect(self.save_new_parameters)
        self.but_defaults.clicked.connect(self.load_default_data)
        self.but_close.clicked.connect(self.exit_procedure)

    # Load the current parameters onto the GUI
    def load_original_data(self):
        pretty_data = yaml.dump(self.parameter_values, default_flow_style=False)
        self.text_box.setText(str(pretty_data))

    # Read defaults to memory
    def load_defaults(self):
        self.default_values = self.p._default

    def validate_data(self):
        self.error = False
        self.current_data = yaml.safe_load(self.text_box.text())
        if isinstance(self.current_data, dict):  # Checking if we did not erase everything
            self.compare_dictionaries(self.default_values, self.current_data)
        else:
            self.error = True

        if self.error:
            self.but_save.setEnabled(False)
            self.iface.messageBar().pushMessage(
                "Error", "Parameter structure was compromised. Please reset " "to defaults", level=3, duration=10
            )
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
                if not isinstance(dict1[key], type(dict2[key])):
                    self.error = True
                    break
                if isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                    self.compare_dictionaries(dict1[key], dict2[key])

            # Check if we did not add a key
            for key in dict2:
                if key not in dict1:
                    self.error = True
                    break
        except Exception as e:
            self.logger.error(e.args)
            self.error = True

    def save_new_parameters(self):
        self.validate_data()
        if not self.error:
            stream = open(self.path, "w")
            yaml.dump(self.current_data, stream, default_flow_style=False)
            stream.close()
            self.but_close.setText("Close")

    def load_default_data(self):
        pretty_data = yaml.dump(self.default_values, default_flow_style=False)
        self.text_box.setText(str(pretty_data))
        self.error = False

    def exit_procedure(self):
        self.close()
