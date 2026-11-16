import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "win32", reason="Requires the HDF5 DLL bundled with QGIS on Windows")
def test_dependencies_import_with_qgis_hdf5_loaded(tmp_path):
    """Regression for https://github.com/AequilibraE/qaequilibrae/issues/638.

    Run with --noconftest to bypass the suite's eager plugin imports when
    diagnosing dependency failures. A fresh process prevents cached imports
    from hiding the DLL conflict.
    """
    packages = Path(__file__).resolve().parents[1] / "qaequilibrae" / "packages"
    script = textwrap.dedent(
        """
        import ctypes
        from pathlib import Path
        import sys

        from qgis.core import QgsApplication

        app = QgsApplication([], False)
        app.initQgis()
        try:
            # OSGeo4W installs QGIS under apps/qgis (or apps/qgis-ltr),
            # with its shared DLLs in the installation's bin directory.
            qgis_hdf5 = Path(QgsApplication.prefixPath()).parents[1] / "bin" / "hdf5.dll"
            assert qgis_hdf5.is_file(), f"QGIS HDF5 DLL not found: {qgis_hdf5}"
            # Keep the handle alive while importing the plugin dependencies.
            hdf5 = ctypes.WinDLL(str(qgis_hdf5))

            sys.path.insert(0, sys.argv[1])
            import h5py
            from aequilibrae.project import Project

            # Exercise the native library as well as Python module imports.
            filename = Path(sys.argv[2]) / "issue_638.h5"
            with h5py.File(filename, "w") as output:
                output.create_dataset("values", data=[1, 2, 3])
            with h5py.File(filename, "r") as source:
                assert source["values"][:].tolist() == [1, 2, 3]
            assert callable(Project)
        finally:
            app.exitQgis()
        """
    )
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    result = subprocess.run(
        [sys.executable, "-c", script, str(packages), str(tmp_path)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, (
        "Plugin dependencies failed with QGIS's HDF5 DLL already loaded (issue #638).\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
