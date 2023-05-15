from os.path import dirname, join

from qgis.PyQt import uic
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog, QTableWidgetItem

from .gtfs_feed import GTFSFeed

FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/gtfs_importer.ui"))


class GTFSImporter(QDialog, FORM_CLASS):
    def __init__(self, _PQgis):
        QDialog.__init__(self)
        self.iface = _PQgis.iface
        self.setupUi(self)

        self._PQgis = _PQgis
        self._p = _PQgis.network

        self.progress_box.setVisible(False)
        self.progress_box.setEnabled(False)
        self.but_add.clicked.connect(self.add_gtfs_feed)
        self.but_execute.clicked.connect(self.execute_importer)
        self.list_feeds.setColumnWidth(0, 230)
        self.feeds = []
        self.done = 1

        self.setFixedHeight(380)
        self.items = [self.config_box, self.progress_box]

    def add_gtfs_feed(self, testing=False):
        dlg2 = GTFSFeed(self._PQgis, testing)
        if not testing:
            dlg2.setWindowFlags(Qt.WindowStaysOnTopHint)
            dlg2.show()
            dlg2.exec_()
        if dlg2.feed is not None:
            self.set_feed(dlg2.feed)

    def set_feed(self, feed):
        if feed is None:
            return
        if "" in [feed.gtfs_data.agency.description, feed.gtfs_data.agency.agency]:
            return

        self.feeds.append(feed)
        self.list_feeds.setRowCount(self.list_feeds.rowCount() + 1)
        feed_txt = QTableWidgetItem(f"{feed.gtfs_data.agency.agency} ({feed.archive_dir})")
        feed_txt.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self.list_feeds.setItem(self.list_feeds.rowCount() - 1, 0, feed_txt)

    def execute_importer(self):
        for item in self.items:
            item.setVisible(not item.isVisible())
            item.setEnabled(not item.isEnabled())
        self.setFixedHeight(176)

        if self.rdo_purge.isChecked() or self.rdo_clear.isChecked():
            self._p.transit.purge(self.rdo_purge.isChecked())

        for i, feed in enumerate(self.feeds):
            feed.signal.connect(self.signal_handler)
            feed.execute_import()

        if self.chb_active_net_rebuild.isChecked():
            walk = self._p.active
            walk.activenet.connect(self.signal_handler)
            walk.build()
        self.close()

    def signal_handler(self, val):
        if len(val) == 1:
            return

        bar = self.progressBar if val[1] == "master" else self.progressBar2
        lbl = self.lbl_progress if val[1] == "master" else self.lbl_progress2

        if val[0] == "start":
            lbl.setText(val[3])
            bar.setRange(0, val[2])
            bar.setValue(0)
        elif val[0] == "update":
            bar.setValue(val[2])
            if val[1] != "master" and bar.maximum() == val[2]:
                self.progressBar.setValue(self.progressBar.value() + 1)
