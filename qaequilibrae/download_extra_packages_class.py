import os
import shutil
import subprocess
import sys
from os.path import join, isdir
from pathlib import Path

import numpy as np
from qgis.core import QgsMessageLog, Qgis


class download_all:
    def __init__(self):
        pth = os.path.dirname(__file__)
        self.file = join(pth, "requirements.txt")
        # self._file = join(pth, "requirements.txt")
        # self.file = join(pth, "requirements_to_do.txt")
        self.pth = join(pth, "packages")

    def install(self):
        # self.adapt_aeq_version()
        with open(self.file, "r") as fl:
            lines = fl.readlines()

        for line in lines:
            self.install_package(line.strip())

        self.clean_packages()

    def install_package(self, package):
        install_command = """-m pip install {package} -t '{self.pth}'"""
        if "aequilibrae" in package.lower():
            install_command += " --no-deps"

        command = f'"{self.find_python()}" {install_command}'
        print(command)
        reps = self.execute(command)

        if "because the ssl module is not available" in "".join(reps).lower() and sys.platform == "win32":
            command = f"python {install_command}"
            print(command)
            reps = self.execute(command)

        for line in reps:
            QgsMessageLog.logMessage(str(line))

    def execute(self, command):
        lines = []
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

        # On mac/windows sys.executable returns '/Applications/QGIS.app/Contents/MacOS/QGIS' or
        # 'C:\\Program Files\\QGIS 3.30.0\\bin\\qgis-bin.exe' respectively so we need to explore in that area
        # of the filesystem
        elif sys.platform == "darwin":
            python_exe = sys_exe.parent / "bin" / "python3"
        elif sys.platform == "win32":
            python_exe = Path(sys.base_prefix) / "python3.exe"

        if not python_exe.exists():
            raise FileExistsError("Can't find a python executable to use")
        print(python_exe)
        return python_exe

    def adapt_aeq_version(self):
        if int(np.__version__.split(".")[1]) >= 22:
            Path(self.file).unlink(missing_ok=True)
            shutil.copyfile(self._file, self.file)
            return

        with open(self._file, "r") as fl:
            cts = [c.rstrip() for c in fl.readlines()]

        with open(self.file, "w") as fl:
            for c in cts:
                if "aequilibrae" in c:
                    c = c + ".dev0"
                fl.write(f"{c}\n")

    def clean_packages(self):
        pkgs = ["numpy", "scipy", "pandas"]
        for fldr in list(os.walk(self.pth))[0][1]:
            for pkg in pkgs:
                if pkg.lower() in fldr.lower():
                    if isdir(join(self.pth, fldr)):
                        shutil.rmtree(join(self.pth, fldr))
