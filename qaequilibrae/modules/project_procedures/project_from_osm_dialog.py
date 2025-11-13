from os.path import isdir, join, dirname

from aequilibrae.context import get_logger
from aequilibrae.project import Project
from aequilibrae.project.network.osm.place_getter import placegetter
from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QVBoxLayout, QGroupBox
from qgis.PyQt.QtWidgets import QRadioButton, QGridLayout, QPushButton, QLineEdit
from qgis.PyQt.QtWidgets import QWidget, QFileDialog, QDialog
from qgis.core import QgsProject, QgsCoordinateReferenceSystem
from shapely.geometry import box

from qaequilibrae.modules.common_tools import reporter, ReportDialog, standard_path, ProgressBar

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "../common_tools/forms/ui_empty.ui"))


class ProjectFromOSMDialog(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.setupUi(self)
        self.qgis_project = qgis_project

        self.path = standard_path()
        self.error = None
        self.report = []
        self.worker_thread = None
        self.running = False
        self.bbox = None
        self.json = []
        self.logger = get_logger()
        self._run_layout = QGridLayout()

        # Area to import network for
        self.choose_place = QRadioButton()
        self.choose_place.setText(self.tr("Place name"))
        self.choose_place.toggled.connect(self.change_place_type)
        self.choose_place.setChecked(False)

        self.choose_canvas = QRadioButton()
        self.choose_canvas.setText(self.tr("Current map canvas area"))
        self.choose_canvas.setChecked(True)

        self.place = QLineEdit()
        self.place.setVisible(False)

        self.source_type_frame = QVBoxLayout()
        self.source_type_frame.setAlignment(Qt.AlignLeft)
        self.source_type_frame.addWidget(self.choose_place)
        self.source_type_frame.addWidget(self.choose_canvas)
        self.source_type_frame.addWidget(self.place)

        self.source_type_widget = QGroupBox(self.tr("Target"))
        self.source_type_widget.setLayout(self.source_type_frame)

        # Buttons and output
        self.but_choose_output = QPushButton()
        self.but_choose_output.setText(self.tr("Choose folder output"))
        self.but_choose_output.clicked.connect(self.choose_output)

        self.output_path = QLineEdit()

        self.but_run = QPushButton()
        self.but_run.setText(self.tr("Import network and create project"))
        self.but_run.clicked.connect(self.run)

        self.buttons_frame = QVBoxLayout()
        self.buttons_frame.addWidget(self.but_choose_output)
        self.buttons_frame.addWidget(self.output_path)
        self.buttons_frame.addWidget(self.but_run)

        self.buttons_widget = QWidget()
        self.buttons_widget.setLayout(self.buttons_frame)

        self._run_layout.addWidget(self.source_type_widget)
        self._run_layout.addWidget(self.buttons_widget)

        self.setLayout(self._run_layout)
        self.resize(280, 250)

    def choose_output(self):
        new_name = QFileDialog.getExistingDirectory(QWidget(), "Parent folder", standard_path())
        if new_name is not None and len(new_name) > 0:
            new_folder = "new_project"
            counter = 1
            while isdir(join(new_name, new_folder)):
                new_folder = f"new_project_{counter}"
                counter += 1
            self.output_path.setText(join(new_name, new_folder))

    def run(self):
        self.resize(280, 300)
        if self.choose_canvas.isChecked():
            self.report.append(reporter("Chose to download network for canvas area"))
            QgsProject.instance().setCrs(QgsCoordinateReferenceSystem.fromEpsgId(4326))
            e = self.iface.mapCanvas().extent()
            bbox = [e.xMinimum(), e.yMinimum(), e.xMaximum(), e.yMaximum()]
        else:
            self.report.append(reporter("Chose to download network for place"))
            bbox, r = placegetter(self.place.text())
            self.report.extend(r)

        self.qgis_project.project = Project()

        progress_bar = ProgressBar(self.qgis_project, self.qgis_project.project)
        progress_bar.worker_thread.new(self.output_path.text())
        progress_bar.worker_thread.network.signal.connect(progress_bar.signal_handler)
        progress_bar.worker_thread.network.create_from_osm(box(*bbox))

        try:
            if progress_bar.worker_thread.network.builder:
                lines = progress_bar.worker_thread.network.count_links()
                nodes = progress_bar.worker_thread.network.count_nodes()
                self.report.append(reporter(f"{lines:,} links generated"))
                self.report.append(reporter(f"{nodes:,} nodes generated"))
                self.leave()
        except AttributeError:
            self.logger.info("Only display builder info")

        progress_bar.finish_procedure()

        dlg2 = ReportDialog(self.iface, self.report)
        dlg2.show()
        dlg2.exec_()

    def change_place_type(self):
        if self.choose_place.isChecked():
            self.place.setVisible(True)
        else:
            self.place.setVisible(False)
