import numpy as np
import importlib.util as iutil
import os
from pathlib import Path
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
        if int(np.__version__.split(".")[1]) < 22:
            self.adapt_aeq_version()

        lines = []
        command = f'"{self.find_python()}" -m pip install -r "{self.file}" -t "{self.pth}" --upgrade'
        print(sys.executable)
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

    def find_python(self):
        sys_exe = Path(sys.executable)
        if sys.platform == "linux" or sys.platform == "linux2":
            # Unlike other platforms, linux uses the system python, lets see if we can guess it
            if Path("/usr/bin/python3").exists():
                return "/usr/bin/python3"
            if Path("/usr/bin/python").exists():
                return "/usr/bin/python"
            # If that didn't work, it also has a valid sys.executable (unlike other platforms)
            python_exe = sys_exe

        # On mac/windows sys.exeuctable returns '/Applications/QGIS.app/Contents/MacOS/QGIS' or
        # 'C:\\Program Files\\QGIS 3.30.0\\bin\\qgis-bin.exe' respectively so we need to explore in that area
        # of the filesystem
        elif sys.platform == "darwin":
            python_exe = sys_exe.parent / "bin" / "python3"
        elif sys.platform == "win32":
            python_exe = sys_exe.parent / "python3.exe"

        if not python_exe.exists():
            raise FileExistsError("Can't find a python executable to use")

        return python_exe

    def adapt_aeq_version(self):
        with open(self.file, "r") as fl:
            cts = [c.rstrip() for c in fl.readlines()]

        with open(self.file, "w") as fl:
            for c in cts:
                if "aequilibrae" in c:
                    c = c + ".dev0"
                fl.write(f"{c}\n")