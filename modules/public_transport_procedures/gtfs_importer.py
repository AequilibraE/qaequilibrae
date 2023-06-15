from os.path import dirname, join, isfile

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QTableWidgetItem

from .gtfs_feed import GTFSFeed

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/gtfs_importer.ui"))


class GTFSImporter(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.setupUi(self)

        self.qgis_project = qgis_project
        self.progress_box.setVisible(False)
        self.progress_box.setEnabled(False)
        self.but_add.clicked.connect(self.add_gtfs_feed)
        self.but_execute.clicked.connect(self.execute_importer)
        self.list_feeds.setColumnWidth(0, 230)
        self.feeds = []
        self.done = 1

        if isfile(join(qgis_project.project.project_base_path, "public_transport.sqlite")):
            self.rdo_clear.setText("Overwrite Routes")
            self.rdo_keep.setText("Add to Existing Routes")
        else:
            self.label_3.setText("Add Transit Table")
            self.rdo_clear.setText("Create New Route System")
            self.rdo_keep.setVisible(False)
            self.rdo_clear.setChecked(True)
        self.setFixedHeight(380)
        self.items = [self.config_box, self.progress_box]

    def add_gtfs_feed(self, testing=False):
        from aequilibrae.transit import Transit

        self._p = Transit(self.qgis_project.project)
        self.dlg2 = GTFSFeed(self.qgis_project, self._p, testing)
        if not testing:
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
        from aequilibrae.project.database_connection import database_connection

        for item in self.items:
            item.setVisible(not item.isVisible())
            item.setEnabled(not item.isEnabled())
        self.setFixedHeight(176)

        if self.rdo_clear.isChecked():
            if isfile(join(self.qgis_project.project.project_base_path, "public_transport.sqlite")):
                self.pt_conn = database_connection("transit")
                for table in [
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
                ]:
                    self.pt_conn.execute(f"DELETE FROM {table};")
                self.pt_conn.commit()

        for _, feed in enumerate(self.feeds):
            feed.signal.connect(self.signal_handler)

            feed.set_allow_map_match(True)
            feed.doWork()

        self.close()

    def signal_handler(self, val):
        if len(val) == 1:
            return

        bar = self.progressBar if val[1] == "master" else self.progressBar2
        lbl = self.lbl_progress if val[1] == "master" else self.lbl_progress2

        print(val)
        if val[0] == "start":
            lbl.setText(val[3])
            bar.setRange(0, val[2])
            bar.setValue(0)
        elif val[0] == "update":
            bar.setValue(val[2])
            if val[1] != "master" and bar.maximum() == val[2]:
                self.progressBar.setValue(self.progressBar.value() + 1)
