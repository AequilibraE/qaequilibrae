import importlib.util as iutil
import os
import subprocess
import sys

from qgis.PyQt import uic, QtWidgets


class download_all:
    def __init__(self):
        pth = os.path.dirname(__file__)
        with open(pth + "/requirements.txt", "r") as req:
            self.packages = [line.rstrip() for line in req.readlines()]

    def install(self):

        lines = []
        for pkg in self.packages:
            spec = iutil.find_spec(pkg)
            if spec is not None:
                continue

            command = f"python -m pip install {pkg} -t {pth}"
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
