from os.path import dirname, join

from qgis.PyQt import QtWidgets, uic


FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "../common_tools/forms/ui_progress_bar.ui"))


class ProgressBar(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgis_project, worker_thread=None):
        QtWidgets.QDialog.__init__(self)
        qgis_project.block_change_scenario()  # We cannot change scenarios in the middle of an ongoing process
        self.setupUi(self)
        self.qgis_project = qgis_project
        self.worker_thread = worker_thread

        # If we have two levels of progress bars, we can remove the next four lines
        for item in [self.pbar_2, self.label_2]:
            item.setVisible(False)
            item.setEnabled(False)
        self.setFixedHeight(90)

        self.finished.connect(self.finish_procedure)

    def run(self):
        self.run_threaded_procedure()
        self.exit_procedure()

    def run_threaded_procedure(self):
        self.worker_thread.signal.connect(self.signal_handler)
        self.worker_thread.start()
        self.exec_()

    def signal_handler(self, val):
        if val[0] == "finished":
            self.exit_procedure()
        elif val[0] == "refresh":
            self.pbar_1.reset()
        elif val[0] == "reset":
            self.pbar_1.reset()
        elif val[0] == "start":
            self.pbar_1.setRange(0, val[1])
            self.label_1.setText(val[2])
        elif val[0] == "set_position":
            self.pbar_1.setValue(val[1])
        elif val[0] == "set_text":
            self.label_1.setText(val[1])
        elif val[0] == "update":
            self.pbar_1.setValue(val[1])
            self.label_1.setText(val[2])

    def exit_procedure(self):
        self.close()
        return self.worker_thread

    def finish_procedure(self):
        """
        Killing the progress bar also kills the parent dialog.
        """
        for widget in QtWidgets.QApplication.topLevelWidgets():
            if isinstance(widget, QtWidgets.QDialog) and widget != self and widget.isVisible():
                widget.close()

        self.qgis_project.message_log("Process interrupted by the user: ")

        self.qgis_project.dialog_depth = -1
        self.qgis_project.allow_change_scenario()
