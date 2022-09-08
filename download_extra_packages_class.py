import os
import subprocess

from qgis.PyQt import uic, QtWidgets
from .common_tools import ReportDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__) + "/forms/", "ui_package_downloader.ui"))


class DownloadExtraPackages(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        with open(os.path.dirname(__file__) + "/extra_requirements.txt", "r") as req:
            self.packages = [line.rstrip() for line in req.readlines()]

        self.lbl_list_of_packages.setText(", ".join(self.packages))
        self.but_download.clicked.connect(self.download_package)
        self.setModal(True)

    def download_package(self):
        lines = []
        for pkg in self.packages:
            command = "python3 -m pip install {}".format(pkg)
            lines.append(command)
            with subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            ) as proc:
                lines.extend(proc.stdout.readlines())

        dlg2 = ReportDialog(self.iface, lines)
        dlg2.show()
        dlg2.exec_()
        self.close()
