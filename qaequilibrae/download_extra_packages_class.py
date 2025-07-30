import os
import shutil
import subprocess
import sys
from importlib.util import find_spec
from os.path import join, isdir
from pathlib import Path

from qgis.core import Qgis, QgsMessageLog


class DownloadAll:
    must_remove = [
        "certifi",
        "charset_normalizer",
        "cpuinfo",
        "geopandas",
        "idna",
        "numpy",
        "packaging",
        "pandas",
        "py_cpuinfo",
        "pyaml",
        "pyarrow",
        "pyogrio",
        "pyproj",
        "pytz",
        "pyyaml",
        "requests",
        "scipy",
        "shapely",
        "tzdata",
        "urllib3",
    ]

    def __init__(self):
        pth = Path(__file__).parent
        self.dependency_files = [pth / "requirements.txt", pth / "aequilibrae_version.txt"]
        self.target_folder = pth / "packages"
        self.no_ssl = False
        self.error = 0

    def install(self):
        command = f'"{self.find_python()}" -m pip install uv'
        _ = self.execute(command)
        print(command)

        for file in self.dependency_files:
            flag = self.target_folder / file.name
            if flag.exists():
                continue

            with open(file, "r") as fl:
                lines = fl.readlines()

            for line in lines:
                self.install_package(line.strip())

            with open(flag, "w") as fl:
                fl.write("")

        self.clean_packages(self.target_folder)
        print("Error code: ", self.error)
        return self.error

    def install_package(self, package):
        Path(self.target_folder).mkdir(parents=True, exist_ok=True)

        spec = find_spec("uv")
        is_uv = "" if spec is None else "uv"

        install_command = f'-m {is_uv} pip install {package} --target "{self.target_folder}"'

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
            QgsMessageLog.logMessage(str(line), level=Qgis.MessageLevel.Info)

        return reps

    def execute(self, command):
        lines = []
        lines.append(command)
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        lines.extend(process.stdout.readlines())
        exit_code = process.wait()
        if exit_code != 0:
            self.error = exit_code
        return lines

    def find_python(self):
        # Check if we're inside a virtual environment
        if sys.prefix != sys.base_prefix:
            return "python3"

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

    def clean_packages(self, target_folder):

        for fldr in list(os.walk(target_folder))[0][1]:
            for pkg in self.must_remove:
                if pkg.lower() in fldr.lower():
                    if isdir(join(target_folder, fldr)):
                        shutil.rmtree(join(target_folder, fldr))
                        QgsMessageLog.logMessage(
                            f"Duplicated packages removed from installation: {fldr}", level=Qgis.MessageLevel.Info
                        )

    def retry_pkg_install(self):
        existing_files = list(os.walk(self.target_folder))[0]
        for packages in existing_files[1]:
            shutil.rmtree(self.target_folder / packages)

        for file in existing_files[2]:
            if file == "__init__.py":
                continue
            (self.target_folder / file).unlink()
        self.install()


if __name__ == "__main__":
    result = DownloadAll().install()

    assert result == 0
