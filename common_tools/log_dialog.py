import os
import tempfile
from qgis.core import *
from qgis.PyQt.Qsci import QsciLexerYAML
from qgis.PyQt.QtGui import *
from qgis.PyQt import QtWidgets, uic
from aequilibrae import Parameters

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_parameters.ui"))


class LogDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        super(LogDialog, self).__init__(parent)
        p = Parameters().parameters

        temp_folder = p["system"]["logging_directory"]
        if not os.path.isdir(temp_folder):
            temp_folder = tempfile.gettempdir()

        self.logfile = log_file = os.path.join(temp_folder, "aequilibrae.log")

        self.iface = iface
        self.setupUi(self)

        self.path = os.path.dirname(os.path.dirname(__file__)) + "/aequilibrae/aequilibrae/"
        self.default_values = None
        self.parameter_values = None
        self.current_data = None
        self.error = False
        # Configures the text editor
        font = QFont()
        font.setFamily("Courier")
        font.setFixedPitch(True)
        font.setPointSize(12)
        lexer = QsciLexerYAML()  # The lexer doesn't really matter
        lexer.setDefaultFont(font)
        self.text_box.setLexer(lexer)
        self.text_box.setFolding(self.text_box.PlainFoldStyle)

        # Load the data
        self.load_data()

        # Connect all buttons
        self.but_validate.setVisible(False)
        self.but_defaults.setVisible(False)
        self.but_save.setVisible(False)
        self.but_close.setText('Close')
        self.but_close.clicked.connect(self.exit_procedure)

    # Load the current parameters onto the GUI
    def load_data(self):
        if not os.path.isfile(self.logfile):
            return
        with open(self.logfile, "r") as log:
            logdata = log.readlines()
        self.text_box.setText(''.join(logdata))

    def exit_procedure(self):
        self.close()
