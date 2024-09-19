import os
import shutil
import subprocess
import sys
from os.path import join, isdir
from pathlib import Path

from qgis.core import QgsMessageLog


class DownloadAll:
    must_remove = [
        "numpy",
        "scipy",
        "pandas",
        "charset_normalizer",
        "click_plugins",
        "click",
        "certifi",
        "cligj",
        "colorama",
        "fiona",
        "pyproj",
        "pytz",
        "requests",
        "rtree",
        "setuptools",
        "shapely",
        "six",
        "tzdata",
        "zipp",
        "attr",
        "attrs",
        "dateutil",
        "python_dateutil",
        "idna",
        "importlib_metadata",
        "pyaml",
        "urllib3",
        "packaging",
        "cpuinfo",
        "py-cpuinfo",
        "geopandas",
        "pyyaml",
        "pyogrio",
    ]

    def __init__(self):
        pth = Path(__file__).parent
        self.dependency_files = [pth / "requirements.txt", pth / "aequilibrae_version.txt"]
        self.target_folder = pth / "packages"
        self.no_ssl = False

    def install(self):
        reps = []
        for file in self.dependency_files:
            flag = self.target_folder / file.name
            if flag.exists():
                continue

            with open(file, "r") as fl:
                lines = fl.readlines()

            for line in lines:
                reps.extend(self.install_package(line.strip()))

            with open(flag, "w") as fl:
                fl.write("")

        self.clean_packages()
        return reps

    def install_package(self, package):
        Path(self.target_folder).mkdir(parents=True, exist_ok=True)

        install_command = f'-m pip install {package} -t "{self.target_folder}"'
        if "ortools" in package.lower():
            install_command += " --no-deps"

        command = f'"{self.find_python()}" {install_command}'
        print(command)

        if not self.no_ssl:
            reps = self.execute(command)

        if self.no_ssl or (
            "because the ssl module is not available" in "".join(reps).lower() and sys.platform == "win32"
        ):
            command = f"python {install_command}"
            print(command)
            reps = self.execute(command)
            self.no_ssl = True

        for line in reps:
            QgsMessageLog.logMessage(str(line))
        return reps

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
        import numpy as np

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

        for fldr in list(os.walk(self.target_folder))[0][1]:
            for pkg in self.must_remove:
                if pkg.lower() in fldr.lower():
                    if isdir(join(self.target_folder, fldr)):
                        shutil.rmtree(join(self.target_folder, fldr))


if __name__ == "__main__":
    result = DownloadAll().install()
    output = ("".join([str(x).upper() for x in result]))
    
    assert "ERROR" not in output

    print(output)