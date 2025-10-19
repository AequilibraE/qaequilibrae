from os.path import dirname, join, isfile

from aequilibrae.transit import Transit
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetItem

from qaequilibrae.modules.common_tools import BaseDialog
from qaequilibrae.modules.transit_procedures import GTFSFeed


class GTFSImporter(BaseDialog):
    def __init__(self, qgis_project):
        super().__init__(
            ui_file=join(dirname(__file__), "forms/gtfs_importer.ui"),
            qgis_project=qgis_project,
        )

    def _base_ui_setup(self):
        self.progress_box.setVisible(False)
        self.progress_box.setEnabled(False)
        self.but_add.clicked.connect(self.add_gtfs_feed)
        self.but_execute.clicked.connect(self.execute_importer)
        self.list_feeds.setColumnWidth(0, 230)
        self.feeds = []
        self.done = 1

        self.is_pt_database = isfile(self.qgis_project.project._transit_database_path)

        if self.is_pt_database:
            self.rdo_clear.setText(self.tr("Overwrite Routes"))
            self.rdo_keep.setText(self.tr("Add to Existing Routes"))
        else:
            self.label_3.setText(self.tr("Add transit table"))
            self.rdo_clear.setText(self.tr("Create new route system"))
            self.rdo_keep.setVisible(False)
            self.rdo_clear.setChecked(True)
        self.setFixedHeight(380)
        self.items = [self.config_box, self.progress_box]

        self.__transit_tables = [
            "agencies",
            "fare_attributes",
            "fare_rules",
            "fare_zones",
            "pattern_mapping",
            "route_links",
            "routes",
            "stop_connectors",
            "stops",
            "trips",
            "trips_schedule",
        ]

    def add_gtfs_feed(self):
        self._p = Transit(self.qgis_project.project)
        self.dlg2 = GTFSFeed(self.qgis_project, self._p)
        self.dlg2.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.dlg2.show()
        self.dlg2.exec_()
        if self.dlg2.feed is not None:
            self.set_feed(self.dlg2.feed)

    def set_feed(self, feed):
        if feed is None:
            return
        if "" in [feed.gtfs_data.agency.description, feed.gtfs_data.agency.agency]:
            return

        self.feeds.append(feed)
        self.list_feeds.setRowCount(self.list_feeds.rowCount() + 1)
        feed_txt = QTableWidgetItem(f"{feed.gtfs_data.agency.agency} ({feed.gtfs_data.feed_date})")
        feed_txt.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self.list_feeds.setItem(self.list_feeds.rowCount() - 1, 0, feed_txt)

    def execute_importer(self):
        for item in self.items:
            item.setVisible(not item.isVisible())
            item.setEnabled(not item.isEnabled())
        self.setFixedHeight(176)

        if self.rdo_clear.isChecked() and self.is_pt_database:
            with self.qgis_project.project.transit_connection as conn:
                for table in self.__transit_tables:
                    conn.execute(f"DELETE FROM {table};")

        for _, feed in enumerate(self.feeds):
            feed.signal.connect(self.signal_handler)
            if self.check_allow_map_match.isChecked():
                feed.set_allow_map_match()
            feed.execute_import()

        self.qgis_project.projectManager.removeTab(0)
        self.qgis_project.update_project_layers()

        self.close()

    def signal_handler(self, val):

        if val[0] == "start":
            self.progressbar.setValue(0)
            self.progressbar.setMaximum(val[1])
            self.progress_label.setText(val[2])
        elif val[0] == "update":
            self.progressbar.setValue(val[1])
            self.progress_label.setText(val[2])
        elif val[0] == "set_text":
            self.progressbar.reset()
            self.progress_label.setText(val[1])
        elif val[0] == "finished":
            self.progressbar.reset()
            self.progress_label.clear()
