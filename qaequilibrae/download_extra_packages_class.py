import os
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from importlib.util import find_spec
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
        self.last_exit_code = 0

    def install(self):
        if sys.platform != "darwin":
            command = [str(self.find_python()), "-m", "pip", "install", "uv"]
            _ = self.execute(command)
            print(" ".join(command))

        for file in self.dependency_files:
            flag = self.target_folder / file.name
            if flag.exists():
                continue

            with open(file, "r") as fl:
                lines = fl.readlines()

            for line in lines:
                package = line.strip()
                if package:
                    self.install_package(package)

            if self.error == 0:
                flag.touch()

        self.clean_packages(self.target_folder)
        print("Error code: ", self.error)
        return self.error

    def install_package(self, package):
        if sys.platform == "darwin" and package.startswith("aequilibrae=="):
            return self.build_aequilibrae_macos(package)

        Path(self.target_folder).mkdir(parents=True, exist_ok=True)

        spec = find_spec("uv")
        # uv probes Python with an isolated process and drops PYTHONHOME. That breaks the
        # relocated Python runtime shipped inside the macOS QGIS application, so use the
        # interpreter's pip there even when uv happens to be installed globally.
        use_uv = spec is not None and sys.platform != "darwin"
        installer = ["uv", "pip"] if use_uv else ["pip"]

        python = str(self.find_python())
        install_command = ["-m", *installer, "install", *package.split(), "--target", str(self.target_folder)]

        # uv chooses an interpreter of its own - virtual environments first, then its managed
        # installs, then whatever is on PATH - instead of the one running this. A QGIS install is
        # not a virtual environment, so uv resolves against some other Python that happens to be
        # around and the wheels it downloads are built for the wrong one: CI landed cp314 wheels
        # beside a QGIS on 3.12, and every compiled module then failed to import. pip needs no
        # such flag, since it always installs for the interpreter that runs it.
        if use_uv and os.path.isabs(python):
            install_command += ["--python", python]

        command = [python, *install_command]
        print(" ".join(command))

        if not self.no_ssl:
            reps = self.execute(command)

        if self.no_ssl or (
            "because the ssl module is not available" in "".join(reps).lower() and sys.platform == "win32"
        ):
            command = ["python", *install_command]
            print(" ".join(command))
            reps = self.execute(command)
            self.no_ssl = True

        for line in reps:
            QgsMessageLog.logMessage(str(line), "Messages", level=Qgis.MessageLevel.Info)

        return reps

    def build_aequilibrae_macos(self, package):
        """Build AequilibraE outside QGIS, then install its wheel into the plugin."""
        # Try to find uv and brew. They should be on the PATH, but if not we'll check the homebrew locations for both Intel and Apple Silicon macs.
        # Expect to find in a homebrew location as the MacOS installation docs recommend installing uv via homebrew.
        # Paths from https://docs.brew.sh/Installation

        uv = shutil.which("uv")
        if uv is None:
            for candidate in (Path("/opt/homebrew/bin/uv"), Path("/usr/local/bin/uv")):
                if candidate.exists():
                    uv = str(candidate)
                    break

        brew = shutil.which("brew")
        if brew is None:
            for candidate in (
                Path("/opt/homebrew/bin/brew"),
                Path("/usr/local/bin/brew"),
            ):
                if candidate.exists():
                    brew = str(candidate)
                    break

        if uv is None or brew is None:
            missing = []
            if uv is None:
                missing.append("uv")
            if brew is None:
                missing.append("Homebrew")
            self.error = 1
            QgsMessageLog.logMessage(
                f"macOS dependency build cannot start; install {', '.join(missing)} first",
                "Messages",
                level=Qgis.MessageLevel.Critical,
            )
            return []

        build_environment = os.environ.copy()
        build_environment.pop("PYTHONHOME", None)

        brew_output = self.execute([brew, "--prefix"], environment=build_environment)
        if self.last_exit_code != 0:
            QgsMessageLog.logMessage(
                "Homebrew could not provide its installation prefix",
                "Messages",
                level=Qgis.MessageLevel.Critical,
            )
            return brew_output

        brew_prefixes = [Path(line.strip()) for line in brew_output[1:] if line.strip()]
        brew_prefix = next((prefix for prefix in reversed(brew_prefixes) if prefix.exists()), None)
        if brew_prefix is None:
            self.error = 1
            QgsMessageLog.logMessage(
                "Homebrew returned an invalid installation prefix",
                "Messages",
                level=Qgis.MessageLevel.Critical,
            )
            return brew_output
        llvm_prefix = brew_prefix / "opt" / "llvm"
        spatialite_library = brew_prefix / "lib"
        compiler = llvm_prefix / "bin" / "clang"
        compiler_cpp = llvm_prefix / "bin" / "clang++"

        if not compiler.exists() or not compiler_cpp.exists():
            self.error = 1
            QgsMessageLog.logMessage(
                "LLVM was not found. Install it with: brew install llvm",
                "Messages",
                level=Qgis.MessageLevel.Critical,
            )
            return []

        if not any(spatialite_library.glob("libspatialite.*")):
            self.error = 1
            QgsMessageLog.logMessage(
                "libspatialite was not found. Install it with: brew install libspatialite",
                "Messages",
                level=Qgis.MessageLevel.Critical,
            )
            return []

        build_environment.update(
            {
                "CC": str(compiler),
                "CXX": str(compiler_cpp),
                "AEQ_SPATIALITE_DIR": str(spatialite_library),
                "DYLD_LIBRARY_PATH": f"{spatialite_library}{os.pathsep}"
                f"{build_environment.get('DYLD_LIBRARY_PATH', '')}",
                "PATH": f"{llvm_prefix / 'bin'}{os.pathsep}{build_environment.get('PATH', '')}",
            }
        )

        build_folder = Path(tempfile.mkdtemp(prefix="qaequilibrae-build-"))
        virtual_environment = build_folder / "venv"
        wheel_folder = build_folder / "wheels"
        wheel_folder.mkdir()
        python_version = f"{sys.version_info[0]}.{sys.version_info[1]}"
        commands = [
            [uv, "python", "install", python_version],
            [uv, "venv", "--python", python_version, "--seed", str(virtual_environment)],
            [
                str(virtual_environment / "bin" / "python"),
                "-m",
                "pip",
                "wheel",
                package,
                "--no-deps",
                "--wheel-dir",
                str(wheel_folder),
            ],
        ]

        try:
            output = []
            for command in commands:
                output.extend(self.execute(command, environment=build_environment))
                if self.last_exit_code != 0:
                    return output

            wheels = list(wheel_folder.glob("aequilibrae-*.whl"))
            if len(wheels) != 1:
                self.error = 1
                QgsMessageLog.logMessage(
                    "The macOS AequilibraE build did not produce exactly one wheel",
                    "Messages",
                    level=Qgis.MessageLevel.Critical,
                )
                return output

            output.extend(self.install_wheel(wheels[0]))
            return output
        finally:
            shutil.rmtree(build_folder, ignore_errors=True)

    def install_wheel(self, wheel):
        """Install a wheel and its runtime dependencies into the plugin package directory."""
        Path(self.target_folder).mkdir(parents=True, exist_ok=True)
        python = str(self.find_python())
        command = [
            python,
            "-m",
            "pip",
            "install",
            str(wheel),
            "--target",
            str(self.target_folder),
        ]
        print(" ".join(command))
        return self.execute(command)

    def execute(self, command, environment=None):
        """Runs *command*, given as an argument list, and returns it followed by its output."""
        lines = []
        lines.append(" ".join(command))
        env = environment
        if env is None and sys.platform == "darwin":
            env = os.environ.copy()
            env["PYTHONHOME"] = str(Path(os.__file__).parents[2])
        # Argument list, no shell: every element is either a literal or a path we resolved ourselves
        process = subprocess.Popen(  # nosec B603
            command,
            stdout=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=env,
        )
        lines.extend(process.stdout.readlines())
        exit_code = process.wait()
        self.last_exit_code = exit_code
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
            python_exe = sys_exe.parent / f"python{sys.version_info[0]}.{sys.version_info[1]}"
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
                    if os.path.isdir(os.path.join(target_folder, fldr)):
                        shutil.rmtree(os.path.join(target_folder, fldr))
                        QgsMessageLog.logMessage(
                            f"Duplicated packages removed from installation: {fldr}",
                            "Messages",
                            level=Qgis.MessageLevel.Info,
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
    sys.exit(DownloadAll().install())
