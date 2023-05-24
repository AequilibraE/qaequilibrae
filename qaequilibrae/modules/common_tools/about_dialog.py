import logging
import os
from os.path import dirname, abspath

import yaml

from qgis.PyQt import QtWidgets, uic
from .auxiliary_functions import standard_path

try:
    from aequilibrae.paths import release_name, release_version
except Exception as e:
    logger = logging.getLogger("AequilibraEGUI")
    logger.error(e.args)
    release_name = "No Binaries available"
    release_version = "No Binaries available"

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_about.ui"))


class AboutDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()

        self.but_close.clicked.connect(self.exit_procedure)

        repository = "https://github.com/AequilibraE/QAequilibraE"

        d = dirname(dirname(dirname(abspath(__file__))))
        with open(os.path.join(d, "meta.yaml"), "r") as yml:
            par = yaml.load(yml)

        my_file = os.path.join(d, "metadata.txt")
        b = "?"
        with open(my_file, "r") as a:
            for line in a.readlines():
                if line[:7] == "version":
                    b = line[8:]
                    break

        self.all_items = []
        self.all_items.append(["AequilibraE Version name", release_name])
        self.all_items.append(["AequilibraE Version number", release_version])
        self.all_items.append(["GUI version", b])
        self.all_items.append(["GUI Repository", repository])
        self.all_items.append(["Minimum QGIS", "3.14"])
        self.all_items.append(["Developers", par["developers"]])
        self.all_items.append(["Sponsors", par["sponsors"]])

        self.assemble()

    def assemble(self):
        titles = []
        row_count = 0

        for r, t in self.all_items:
            titles.append(r)
            self.about_table.insertRow(row_count)
            if isinstance(t, list):
                lv = QtWidgets.QListWidget()
                lv.addItems(t)
                self.about_table.setCellWidget(row_count, 0, lv)
                self.about_table.setRowHeight(row_count, len(t) * self.about_table.rowHeight(row_count))
            else:
                self.about_table.setItem(row_count, 0, QtWidgets.QTableWidgetItem(str(t)))

            row_count += 1
        self.about_table.setVerticalHeaderLabels(titles)

    def exit_procedure(self):
        self.close()
