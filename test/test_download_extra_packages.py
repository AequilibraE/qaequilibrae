from pathlib import Path

from qaequilibrae.download_extra_packages_class import DownloadAll


def _captured_command(mocker, python, tmp_path):
    """Run install_package with subprocess execution stubbed and return its argv."""
    mocker.patch.object(DownloadAll, "find_python", return_value=python)

    calls = []
    mocker.patch.object(DownloadAll, "execute", side_effect=lambda command: calls.append(command) or [])

    installer = DownloadAll()
    installer.target_folder = tmp_path / "packages"
    installer.install_package("aequilibrae==1.7.0")
    return calls[0]


def test_pip_runs_with_the_qgis_interpreter(mocker, tmp_path):
    python = str(tmp_path / "apps" / "Python312" / "python3.exe")

    command = _captured_command(mocker, python, tmp_path)

    assert command[1:4] == ["-m", "pip", "install"]
    assert "--python" not in command


def test_find_python_finds_versioned_macos_executable(mocker, tmp_path):
    contents = tmp_path / "QGIS.app" / "Contents"
    executable = contents / "MacOS" / "python3.12"
    executable.parent.mkdir(parents=True)
    executable.touch()
    executable.chmod(0o755)
    mocker.patch("qaequilibrae.download_extra_packages_class.sys.platform", "darwin")
    mocker.patch("qaequilibrae.download_extra_packages_class.sys.executable", str(contents / "MacOS" / "QGIS"))
    mocker.patch("qaequilibrae.download_extra_packages_class.sys.prefix", "/qgis")
    mocker.patch("qaequilibrae.download_extra_packages_class.sys.base_prefix", "/qgis")

    command = DownloadAll().find_python()

    assert command == Path(executable)
