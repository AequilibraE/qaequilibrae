import importlib.util as iutil
import os
import subprocess

from qgis.PyQt import uic, QtWidgets


class download_all:
    def __init__(self):
        with open(os.path.dirname(__file__) + "/requirements.txt", "r") as req:
            self.packages = [line.rstrip() for line in req.readlines()]

    def install(self):

        lines = []
        for pkg in self.packages:
            spec = iutil.find_spec(pkg)
            if spec is not None:
                continue

            command = "python3 -m pip install --user {}".format(pkg)
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
