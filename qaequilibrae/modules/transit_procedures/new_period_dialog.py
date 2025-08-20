from os.path import join, dirname

from qgis.PyQt import QtWidgets, uic, QtCore

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/ui_add_period.ui"))


class NewPeriodDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QtWidgets.QDialog.__init__(self, None, QtCore.Qt.WindowStaysOnTopHint)
        self.iface = iface
        self.setupUi(self)
        self.error = []

        self.but_add.clicked.connect(self.exit_procedure)

    def exit_procedure(self):
        self.start_time = self.__time_converter(self.time_start.time())
        self.end_time = self.__time_converter(self.time_end.time())
        self.description = self.ln_period_desc.text()
        self.close()

    def __time_converter(self, time):
        seconds = time.hour() * 3_600 + time.minute() * 60 + time.second()
        return seconds
