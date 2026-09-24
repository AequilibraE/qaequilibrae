from os.path import dirname, join

from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal
from qgis.PyQt.QtWidgets import QTableWidgetItem, QAbstractItemView
from qgis.core import QgsProcessingFeedback

from qaequilibrae.modules.common_tools import BaseDialog
from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.modules.processing_provider.paths_procedures.network_skimming import (
    NetworkSkimming,
    run_network_skimming,
)


class SkimmingFeedback(QgsProcessingFeedback):
    """Forward Processing progress to the dialog while it runs on a worker thread."""

    message = pyqtSignal(str)

    def __init__(self, cancellation_requested):
        super().__init__()
        self.cancellation_requested = cancellation_requested

    def pushInfo(self, message):
        super().pushInfo(message)
        self.message.emit(message)

    def isCanceled(self):
        return self.cancellation_requested() or super().isCanceled()


class SkimmingWorker(QThread):
    message = pyqtSignal(str)
    progress = pyqtSignal(float)

    def __init__(self, parameters, project, parent):
        super().__init__(parent)
        self.parameters = parameters
        self.project = project
        self.error = None
        self.result = None
        self.cancel_requested = False

    def cancel(self):
        self.cancel_requested = True

    def run(self):
        try:
            feedback = SkimmingFeedback(lambda: self.cancel_requested)
            feedback.message.connect(self.message.emit)
            feedback.progressChanged.connect(self.progress.emit)
            self.result = run_network_skimming(self.parameters, self.project, feedback)
        except Exception as error:
            self.error = str(error)


class ImpedanceMatrixDialog(BaseDialog):
    def __init__(self, qgis_project):
        super().__init__(ui_file=join(dirname(__file__), "forms/ui_impedance_matrix.ui"), qgis_project=qgis_project)

    def _base_ui_setup(self, **kwargs):
        self.link_layer = self.qgis_project.layers["links"][0]
        self.tot_skims = 0
        self.name_skims = 0
        self.graph = None
        self.skimmeable_fields = []
        self.skim_fields = []
        self.all_modes = {}
        self.error = None
        self.worker_thread = None
        self.processing_results = None

        # FIRST, we connect slot signals
        # For adding skims
        self.but_adds_to_links.clicked.connect(self.append_to_list)
        self.but_removes_from_links.clicked.connect(self.removes_fields)
        self.do_dist_matrix.clicked.connect(self.run_skimming)

        # SECOND, we set visibility for sections that should not be shown when the form opens (overlapping items)
        #        and re-dimension the items that need re-dimensioning
        self.hide_all_progress_bars()
        self.available_skims_table.setColumnWidth(0, 245)
        self.skim_list.setColumnWidth(0, 245)
        self.available_skims_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.skim_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # loads default path from parameters
        self.path = standard_path()

        self.cb_minimizing.clear()
        self.available_skims_table.clearContents()
        self.block_paths.setChecked(True)

        with self.project.db_connection as conn:
            res = conn.execute("""select mode_name, mode_id from modes""")
            for x in res.fetchall():
                self.cb_modes.addItem(f"{x[0]} ({x[1]})")
                self.all_modes[f"{x[0]} ({x[1]})"] = x[1]

        self.skimmeable_fields = self.project.network.skimmable_fields()
        self.available_skims_table.setRowCount(len(self.skimmeable_fields))
        for i, q in enumerate(self.skimmeable_fields):
            self.cb_minimizing.addItem(q)
            self.available_skims_table.setItem(i, 0, QTableWidgetItem(q))

    def removes_fields(self):
        table = self.available_skims_table
        final_table = self.skim_list

        for i in final_table.selectedRanges():
            old_fields = [final_table.item(row, 0).text() for row in range(i.topRow(), i.bottomRow() + 1)]

            for row in range(i.bottomRow(), i.topRow() - 1, -1):
                final_table.removeRow(row)

            counter = table.rowCount()
            for field in old_fields:
                table.setRowCount(counter + 1)
                item1 = QTableWidgetItem(field)
                item1.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                table.setItem(counter, 0, item1)
                counter += 1

    def append_to_list(self):
        table = self.available_skims_table
        final_table = self.skim_list

        for i in table.selectedRanges():
            new_fields = [table.item(row, 0).text() for row in range(i.topRow(), i.bottomRow() + 1)]

            for f in new_fields:
                self.skim_fields.append(self.only_str(f))
            for row in range(i.bottomRow(), i.topRow() - 1, -1):
                table.removeRow(row)

            counter = final_table.rowCount()
            for field in new_fields:
                final_table.setRowCount(counter + 1)
                item1 = QTableWidgetItem(field)
                item1.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                final_table.setItem(counter, 0, item1)
                counter += 1

    def hide_all_progress_bars(self):
        self.progressbar.setVisible(False)
        self.progress_label.setVisible(False)
        self.progressbar.setValue(0)
        self.progress_label.setText("")

    def check_name_exists(self):
        with self.project.db_connection as conn:
            txt = self.line_matrix.text()
            if not len(txt):
                return False
            if conn.execute("Select count(*) from matrices where name=?", [txt]).fetchone()[0]:
                return False
            return True

    def run_thread(self):
        self.worker_thread.finished.connect(self.job_finished_from_thread)
        self.worker_thread.start()
        self.exec()

    def job_finished_from_thread(self):
        self.worker_thread.wait()
        self.error = self.worker_thread.error
        self.processing_results = self.worker_thread.result
        if self.error:
            self.qgis_project.iface_error_message(self.error, self.tr("Input error"))
        self.exit_procedure()

    def run_skimming(self):  # Saving results
        if not self.check_name_exists():
            return
        self.mat_name = self.line_matrix.text()
        self.processing_results = None
        self.funding1.setVisible(False)
        self.funding2.setVisible(False)
        self.progressbar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progressbar.setRange(0, 100)
        self.progressbar.setValue(0)
        self.do_dist_matrix.setVisible(False)

        # The dialog only translates its state into Processing parameters. Graph
        # preparation, validation and saving belong to the reusable algorithm.
        self.worker_thread = SkimmingWorker(self.processing_parameters(), self.project, self)
        self.worker_thread.message.connect(self.progress_label.setText)
        self.worker_thread.progress.connect(self._set_progress)
        self.run_thread()

    def _set_progress(self, value):
        self.progressbar.setValue(int(value))

    def processing_parameters(self):
        """Translate widget values into the public Processing inputs."""
        algorithm = NetworkSkimming
        excluded_links = []
        if self.chb_chosen_links.isChecked():
            link_id_index = self.link_layer.fields().lookupField("link_id")
            excluded_links = [feature.attribute(link_id_index) for feature in self.link_layer.selectedFeatures()]

        return {
            algorithm.PROJECT_FOLDER: str(self.project.project_base_path),
            algorithm.MODE: self.all_modes[self.cb_modes.currentText()],
            algorithm.COST_FIELD: self.cb_minimizing.currentText(),
            algorithm.SKIM_FIELDS: ",".join(self.skim_fields),
            algorithm.TRACE_ALL_NODES: self.rdo_all_nodes.isChecked(),
            algorithm.BLOCK_CENTROID_FLOWS: self.block_paths.isChecked(),
            algorithm.EXCLUDED_LINKS: ",".join(str(link_id) for link_id in excluded_links),
            algorithm.MATRIX_NAME: self.mat_name,
        }

    @staticmethod
    def only_str(str_input):
        if isinstance(str_input, bytes):
            return str_input.decode("utf-8")
        return str_input

    def exit_procedure(self):
        self.close()
