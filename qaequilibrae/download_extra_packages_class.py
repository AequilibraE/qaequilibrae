import logging
import glob
import os
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from importlib.util import find_spec
from pathlib import Path

from qgis.core import Qgis

if __package__:
    from qaequilibrae.qgis_logging import get_logger
else:
    # Windows CI executes this module directly from the plugin directory, where importing
    # ``qaequilibrae`` would resolve to qaequilibrae.py instead of the package.
    from qgis_logging import get_logger


LOGGER = get_logger(__name__)


def log_message(message, level: Qgis.MessageLevel = Qgis.MessageLevel.Info, notify_user: bool = True):
    """Write dependency-installation messages through the plugin logger."""
    python_level = {
        Qgis.MessageLevel.Critical: logging.ERROR,
        Qgis.MessageLevel.Warning: logging.WARNING,
    }.get(level, logging.INFO)
    LOGGER.log(python_level, message, extra={"qgis_level": level, "notify_user": notify_user})


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
        self.target_folder.mkdir(parents=True, exist_ok=True)

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
            reps = self.build_aequilibrae_macos(package)
            for line in reps:
                log_message(str(line))
            return reps

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
            log_message(str(line))

        return reps

    def build_aequilibrae_macos(self, package):
        """Build AequilibraE outside QGIS, then install its wheel into the plugin."""
        uv = self._find_macos_tool("uv")
        brew = self._find_macos_tool("brew")

        if brew is None:
            self.error = 1
            log_message(
                "macOS dependency build cannot start; install Homebrew first",
                Qgis.MessageLevel.Critical,
            )
            return []

        build_environment = os.environ.copy()
        build_environment.pop("PYTHONHOME", None)

        brew_output = self.execute([brew, "--prefix"], environment=build_environment)
        if self.last_exit_code != 0:
            log_message(
                "Homebrew could not provide its installation prefix",
                Qgis.MessageLevel.Critical,
            )
            return brew_output

        brew_prefixes = [Path(line.strip()) for line in brew_output[1:] if line.strip()]
        brew_prefix = next((prefix for prefix in reversed(brew_prefixes) if prefix.exists()), None)
        if brew_prefix is None:
            self.error = 1
            log_message(
                "Homebrew returned an invalid installation prefix",
                Qgis.MessageLevel.Critical,
            )
            return brew_output
        llvm_prefix = brew_prefix / "opt" / "llvm"
        spatialite_library = brew_prefix / "lib"
        compiler = llvm_prefix / "bin" / "clang"
        compiler_cpp = llvm_prefix / "bin" / "clang++"

        if not compiler.exists() or not compiler_cpp.exists():
            self.error = 1
            log_message(
                "LLVM was not found. Install it with: brew install llvm",
                Qgis.MessageLevel.Critical,
            )
            return []

        if not any(spatialite_library.glob("libspatialite.*")):
            self.error = 1
            log_message(
                "libspatialite was not found. Install it with: brew install libspatialite",
                Qgis.MessageLevel.Critical,
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

        if uv is None:
            # Fall back to building directly with pip if Homebrew Python headers exist
            py_ver = f"{sys.version_info[0]}.{sys.version_info[1]}"
            py_include = None
            for pattern in [
                brew_prefix / f"opt/python@{py_ver}/Frameworks/Python.framework/Versions/{py_ver}/include/python{py_ver}",
                brew_prefix / f"Cellar/python@{py_ver}" / "*" / f"Frameworks/Python.framework/Versions/*/include/python*",
            ]:
                for m in [Path(p) for p in glob.glob(str(pattern))]:
                    if (m / "Python.h").exists():
                        py_include = m
                        break
                if py_include:
                    break

            if py_include:
                direct_env = build_environment.copy()
                direct_env["CPPFLAGS"] = f"-I{py_include} -I{llvm_prefix / 'include'} " + direct_env.get("CPPFLAGS", "")
                direct_env["LDFLAGS"] = f"-L{llvm_prefix / 'lib'} -Wl,-rpath,{llvm_prefix / 'lib'} " + direct_env.get("LDFLAGS", "")
                python = str(self.find_python())
                cmd = [python, "-m", "pip", "install", package, "--target", str(self.target_folder)]
                return self.execute(cmd, environment=direct_env)

            self.error = 1
            log_message(
                "macOS dependency build cannot start; install uv (brew install uv) or python@3.12 (brew install python@3.12)",
                Qgis.MessageLevel.Critical,
            )
            return []

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
                log_message(
                    "The macOS AequilibraE build did not produce exactly one wheel",
                    Qgis.MessageLevel.Critical,
                )
                return output

            output.extend(self.install_wheel(wheels[0]))
            return output
        finally:
            shutil.rmtree(build_folder, ignore_errors=True)

    @staticmethod
    def _find_macos_tool(name):
        """Find a macOS build tool outside the environment QGIS inherits."""
        executable = shutil.which(name)
        if executable is not None:
            return executable

        for candidate in (
            Path.home() / ".local" / "bin" / name,
            Path("/opt/homebrew/bin") / name,
            Path("/usr/local/bin") / name,
        ):
            if candidate.exists():
                return str(candidate)

        return None

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
        with subprocess.Popen(  # nosec B603
            command,
            stdout=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env=env,
        ) as process:
            output, _ = process.communicate()
            lines.extend(output.splitlines(keepends=True))
            exit_code = process.returncode
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
            # On macOS, QGIS runs from an app bundle where sys.executable is
            # /Applications/QGIS.app/Contents/MacOS/QGIS.
            # The python wrapper script is at /Applications/QGIS.app/Contents/MacOS/python
            # (which sets PYTHONHOME appropriately for relocatable execution).
            candidates = [
                sys_exe.parent / "python",
                sys_exe.parent / f"python{sys.version_info[0]}.{sys.version_info[1]}",
                sys_exe.parent / "python3",
                sys_exe.parent / "bin" / "python3",
                sys_exe.parent / "bin" / "python",
                Path(sys.base_prefix) / "bin" / "python3",
                Path(sys.base_prefix) / "bin" / "python",
                Path(sys.prefix) / "bin" / "python3",
                Path(sys.prefix) / "bin" / "python",
            ]
            for candidate in candidates:
                if candidate.exists() and os.access(candidate, os.X_OK):
                    python_exe = candidate
                    break
        elif sys.platform == "win32":
            candidates = [
                Path(sys.base_prefix) / "python3.exe",
                Path(sys.base_prefix) / "python.exe",
                Path(sys.prefix) / "python3.exe",
                Path(sys.prefix) / "python.exe",
                sys_exe.parent / "python3.exe",
                sys_exe.parent / "python.exe",
            ]
            for candidate in candidates:
                if candidate.exists():
                    python_exe = candidate
                    break

        if python_exe is None or not python_exe.exists():
            for name in [f"python{sys.version_info[0]}.{sys.version_info[1]}", "python3", "python"]:
                which_path = shutil.which(name)
                if which_path:
                    python_exe = Path(which_path)
                    break

        if python_exe is None or not python_exe.exists():
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
        if not os.path.exists(target_folder):
            return
        walk_result = list(os.walk(target_folder))
        if not walk_result:
            return

        for fldr in walk_result[0][1]:
            for pkg in self.must_remove:
                if pkg.lower() in fldr.lower():
                    pkg_path = os.path.join(target_folder, fldr)
                    if os.path.isdir(pkg_path):
                        shutil.rmtree(pkg_path)
                        log_message(
                            f"Duplicated packages removed from installation: {fldr}",
                        )

    def retry_pkg_install(self):
        if not os.path.exists(self.target_folder):
            self.install()
            return
        walk_result = list(os.walk(self.target_folder))
        if not walk_result:
            self.install()
            return

        for packages in walk_result[0][1]:
            shutil.rmtree(self.target_folder / packages)

        for file in walk_result[0][2]:
            if file == "__init__.py":
                continue
            (self.target_folder / file).unlink()
        self.install()


if __name__ == "__main__":
    sys.exit(DownloadAll().install())
