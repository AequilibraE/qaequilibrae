import os
import tempfile
from os.path import join

from aequilibrae.parameters import Parameters
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.Qsci import QsciLexerYAML
from qgis.PyQt.QtGui import QFont

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_parameters.ui"))


class LogDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project, parent=None):
        super(LogDialog, self).__init__(parent)

        self.logfile = join(qgis_project.project.project_base_path, "aequilibrae.log")

        self.iface = qgis_project.iface
        self.setupUi(self)
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
        self.but_save.setVisible(True)
        self.but_close.setText("Close")
        self.but_close.clicked.connect(self.exit_procedure)
        self.but_save.clicked.connect(self.save_to_disk)

    # Load the current parameters onto the GUI
    def load_data(self):
        if not os.path.isfile(self.logfile):
            return
        with open(self.logfile, "r") as log:
            logdata = log.readlines()
        self.text_box.setText("".join(logdata))

    def save_to_disk(self):
        with open(self.logfile, "w") as log:
            log.writelines(self.text_box.text())

    def exit_procedure(self):
        self.close()
