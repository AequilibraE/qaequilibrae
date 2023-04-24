import importlib.util as iutil
import os
import subprocess
import sys
from os.path import join
from qgis.PyQt import uic, QtWidgets


class download_all:
    def __init__(self):
        pth = os.path.dirname(__file__)
        with open(pth + "/requirements.txt", "r") as req:
            self.packages = [line.rstrip() for line in req.readlines()]
        self.pth = join(pth, "packages")

    def install(self):
        print(packages)
        lines = []
        for pkg in self.packages:
            spec = iutil.find_spec(pkg)
            if spec is not None:
                continue

            command = f"python -m pip install {pkg} -t {self.pth}"
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
