import logging
import os
from os.path import dirname, abspath
import requests
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
            par = yaml.safe_load(yml)

        my_file = os.path.join(d, "metadata.txt")
        b = "?"
        with open(my_file, "r") as a:
            for line in a.readlines():
                if line[:18] == "qgisMinimumVersion":
                    min_qgis = line[19:-1] if line[-1] == "\n" else line[19:]
                    continue
                if line[:7] == "version":
                    b = line[8:-1] if line[-1] == "\n" else line[8:]
                    break

        developers = self.get_contributors(repository)

        self.all_items = []
        self.all_items.append([self.tr("AequilibraE Version name"), release_name])
        self.all_items.append([self.tr("AequilibraE Version number"), release_version])
        self.all_items.append([self.tr("GUI version"), b])
        self.all_items.append([self.tr("GUI Repository"), repository])
        self.all_items.append([self.tr("Minimum QGIS"), min_qgis])
        self.all_items.append([self.tr("Developers"), developers])
        self.all_items.append([self.tr("Sponsors"), par["sponsors"]])

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
                self.about_table.setItem(row_count, 0, QtWidgets.QTableWidgetItem(self.tr(t)))

            row_count += 1
        self.about_table.setVerticalHeaderLabels(titles)

    def get_contributors(self, repo_url):
        repo_name = repo_url.split("/")[-1]
        owner_name = repo_url.split("/")[-2]
        api_url = f"https://api.github.com/repos/{owner_name}/{repo_name}/contributors"
        response = requests.get(api_url)
        if response.status_code == 200:
            contributors = [user["login"] for user in response.json()]
            return [x for x in contributors if "[bot]" not in x]
        else:
            return None

    def exit_procedure(self):
        self.close()
