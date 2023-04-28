import importlib.util as iutil
import os
import subprocess
import sys
from os.path import join
from qgis.PyQt import uic, QtWidgets
from qgis.core import QgsMessageLog, Qgis


class download_all:
    def __init__(self):
        pth = os.path.dirname(__file__)
        self.file = join(pth, "requirements.txt")
        self.pth = join(pth, "packages")

    def install(self):
        lines = []
        command = f"python -m pip install -r {self.file} -t {self.pth} --upgrade"
        print(command)
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

        for line in lines:
            QgsMessageLog.logMessage(str(line), level=Qgis.Critical)
        return lines
