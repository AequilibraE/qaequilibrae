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
    diagnosing dependency failures. Compare fresh processes so cached imports
    cannot hide the conflict, and a general import failure is distinguishable
    from a failure after QGIS loads its HDF5 DLL.
    """
    packages = Path(__file__).resolve().parents[1] / "qaequilibrae" / "packages"
    script = textwrap.dedent(
        """
        import ctypes
        from ctypes import wintypes
        from importlib.metadata import distribution
        from importlib.util import find_spec
        from pathlib import Path
        import sys

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = wintypes.HMODULE
        kernel32.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
        kernel32.GetModuleFileNameW.restype = wintypes.DWORD

        def report_hdf5():
            handle = kernel32.GetModuleHandleW("hdf5.dll")
            if not handle:
                print("Loaded hdf5.dll: none", flush=True)
                return
            filename = ctypes.create_unicode_buffer(32768)
            if not kernel32.GetModuleFileNameW(handle, filename, len(filename)):
                raise ctypes.WinError(ctypes.get_last_error())
            print(f"Loaded hdf5.dll: {filename.value}", flush=True)

        packages = Path(sys.argv[1]).resolve()
        sys.path.insert(0, str(packages))
        spec = find_spec("h5py")
        assert spec is not None, "h5py is not installed"
        print(f"h5py origin: {spec.origin}", flush=True)
        assert Path(spec.origin).resolve().is_relative_to(packages), "h5py must come from the plugin packages"
        for name in ("h5py", "aequilibrae"):
            package = distribution(name)
            print(f"{name}: {package.version} at {package.locate_file('')}", flush=True)

        report_hdf5()
        if sys.argv[3] == "qgis":
            print("Initializing QGIS", flush=True)
            from qgis.core import QgsApplication

            app = QgsApplication([], False)
            app.initQgis()
            report_hdf5()
            # OSGeo4W installs QGIS under apps/qgis (or apps/qgis-ltr),
            # with its shared DLLs in the installation's bin directory.
            qgis_hdf5 = Path(QgsApplication.prefixPath()).parents[1] / "bin" / "hdf5.dll"
            assert qgis_hdf5.is_file(), f"QGIS HDF5 DLL not found: {qgis_hdf5}"
            print(f"Preloading QGIS HDF5: {qgis_hdf5}", flush=True)
            hdf5 = ctypes.WinDLL(str(qgis_hdf5))
            report_hdf5()

        try:
            print("Importing h5py", flush=True)
            import h5py

            print(f"h5py HDF5 runtime: {h5py.version.hdf5_version}", flush=True)
            print("Importing aequilibrae.project.Project", flush=True)
            from aequilibrae.project import Project

            filename = Path(sys.argv[2]) / (sys.argv[3] + ".h5")
            with h5py.File(filename, "w") as output:
                output.create_dataset("values", data=[1, 2, 3])
            with h5py.File(filename, "r") as source:
                assert source["values"][:].tolist() == [1, 2, 3]
        finally:
            report_hdf5()
        # Let process exit release QGIS. exitQgis() can crash while Python
        # still owns wrappers for destroyed C++ objects (see pytest.ini).
        """
    )
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    results = {}
    for mode in ("clean", "qgis"):
        results[mode] = subprocess.run(
            [sys.executable, "-c", script, str(packages), str(tmp_path), mode],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    diagnostics = "\n\n".join(
        f"{mode} process (exit {result.returncode})\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        for mode, result in results.items()
    )
    assert results["clean"].returncode == 0, (
        "Dependencies fail without importing QGIS; this does not establish a QGIS HDF5 DLL conflict.\n" + diagnostics
    )
    assert results["qgis"].returncode == 0, (
        "The clean process passed, but the QGIS/HDF5 preload process failed (issue #638). "
        "Inspect the last completed stage and DLL paths below; an import failure alone does not prove a DLL conflict.\n"
        + diagnostics
    )
