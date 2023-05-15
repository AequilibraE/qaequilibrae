from copy import deepcopy
from os.path import dirname, join

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QDate
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QTableWidgetItem

from ..common_tools import GetOutputFileName

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/gtfs_feed.ui"))


class GTFSFeed(QDialog, FORM_CLASS):
    def __init__(self, _PQgis, testing=False):
        QDialog.__init__(self)
        self.iface = _PQgis.iface
        self.setupUi(self)
        self._PQgis = _PQgis
        self._p = _PQgis.network
        self.worker_thread = self._p.tools
        self.feed = None
        self.but_add.clicked.connect(self.return_feed)
        self.but_new_row.clicked.connect(self.new_route_capacities)
        self.default_capacities = {}

        self.items = [self.but_add, self.service_calendar]
        self.but_add.setVisible(False)
        self.service_calendar.setVisible(False)
        self.setFixedHeight(1)
        if testing:
            self.close()
        else:
            self.open_feed()
            if self.feed is None:
                self.close()

    def open_feed(self):
        formats = ["GTFS Feed(*.zip)"]
        source_path_file, _ = GetOutputFileName(
            QDialog(),
            "Target GTFS feed",
            formats,
            ".sqlite",
            self._PQgis.path,
        )
        if source_path_file is not None:
            self.set_data(source_path_file)

    def set_data(self, source_path_file):
        for item in self.items:
            item.setVisible(not item.isVisible())
        self.setMinimumHeight(370)
        self.feed = self._p.transit.new_gtfs(agency="", file_path=source_path_file)
        if dates := self.feed.dates_available():
            dates = [QDate.fromString(dt, "yyyy-MM-dd") for dt in dates]
            md = min(dates)
            self.service_calendar.setMinimumDate(md)
            self.service_calendar.setSelectedDate(md)
            self.service_calendar.setMaximumDate(max(dates))
        self.default_capacities = deepcopy(self._p.transit.default_capacities)
        self.tbl_capacities.clearContents()
        self.tbl_capacities.setRowCount(len(self.default_capacities.values()))
        for i, (key, val) in enumerate(self.default_capacities.items()):
            mode = QTableWidgetItem(str(key))
            mode.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.tbl_capacities.setItem(i, 0, mode)
            for j, v in enumerate(val):
                self.tbl_capacities.setItem(i, j + 1, QTableWidgetItem(str(v)))

    def return_feed(self):
        descr = self.led_description.text()
        ag = self.led_agency.text()
        if "" in [descr, ag]:
            self.iface.messageBar().pushMessage("Error", "Enter agency and description", level=3, duration=10)
            return

        date = self.service_calendar.selectedDate().toString("yyyy-MM-dd")
        self.feed.set_date(date)
        self.feed.set_do_raw_shapes(self.chb_raw_shapes.isChecked())

        caps = {}
        for row in range(self.tbl_capacities.rowCount()):
            key = self.tbl_capacities.item(row, 0).text()
            key = int(key) if key.isdigit() else key
            v1 = float(self.tbl_capacities.item(row, 1).text())
            v2 = float(self.tbl_capacities.item(row, 2).text())
            v3 = float(self.tbl_capacities.item(row, 3).text())
            caps[key] = [v1, v2, v3]

        self.feed.gtfs_data.agency.description = descr
        self.feed.gtfs_data.agency.agency = ag
        self.feed.__capacities__ = caps
        self._p.transit.default_capacities = caps
        self.close()

    def new_route_capacities(self):
        self.tbl_capacities.setRowCount(self.tbl_capacities.rowCount() + 1)
