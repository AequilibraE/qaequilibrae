from os.path import dirname, join, isfile

from aequilibrae.transit import Transit
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QTableWidgetItem

from qaequilibrae.modules.common_tools import BaseDialog, ProgressBar
from qaequilibrae.modules.transit_procedures import GTFSFeed


class GTFSImporter(BaseDialog):
    def __init__(self, qgis_project):
        super().__init__(
            ui_file=join(dirname(__file__), "forms/gtfs_importer.ui"),
            qgis_project=qgis_project,
        )

    def _base_ui_setup(self):
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
        if self.rdo_clear.isChecked() and self.is_pt_database:
            with self.qgis_project.project.transit_connection as conn:
                for table in self.__transit_tables:
                    conn.execute(f"DELETE FROM {table};")

        dlg = ProgressBar(self.qgis_project)
        dlg.setWindowFlags(Qt.WindowStaysOnTopHint)
        dlg.show()

        for i, feed in enumerate(self.feeds):
            dlg.pbar_1.setMinimum(0)
            dlg.pbar_1.setMaximum(len(self.feeds))
            dlg.pbar_1.setValue(i)
            dlg.label_1.setText(f"Processando feed {i+1} de {len(self.feeds)}: {feed.gtfs_data.agency.agency}")
            feed.signal.connect(dlg.signal_handler)
            if self.check_allow_map_match.isChecked():
                feed.set_allow_map_match()
            if i == 0:
                dlg.exec_()
            feed.execute_import()

        dlg.pbar_1.setValue(len(self.feeds))
        dlg.label_1.setText("Importação concluída!")
        dlg.exit_procedure()

        self.qgis_project.projectManager.removeTab(0)
        self.qgis_project.update_project_layers()

        self.close()
