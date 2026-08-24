from pathlib import Path

from qaequilibrae.download_extra_packages_class import DownloadAll


def _captured_command(mocker, python, uv_available):
    """Runs install_package with the subprocess call stubbed, and returns the argv it built."""
    mocker.patch(
        "qaequilibrae.download_extra_packages_class.find_spec",
        return_value=object() if uv_available else None,
    )
    mocker.patch.object(DownloadAll, "find_python", return_value=python)

    calls = []
    mocker.patch.object(DownloadAll, "execute", side_effect=lambda command: calls.append(command) or [])

    DownloadAll().install_package("aequilibrae==1.7.0")
    return calls[0]


def test_uv_is_pinned_to_the_interpreter_that_will_import_the_packages(mocker, tmp_path):
    """uv picks an interpreter of its own, and would otherwise fetch wheels for the wrong one.

    CI installed cp314 wheels next to a QGIS running 3.12, so every compiled AequilibraE module
    was missing as far as that interpreter was concerned.
    """
    python = str(tmp_path / "apps" / "Python312" / "python3.exe")

    command = _captured_command(mocker, python, uv_available=True)

    assert command[0] == python
    assert command[1:4] == ["-m", "uv", "pip"]
    assert "--python" in command, "uv was left to choose an interpreter on its own"
    assert command[command.index("--python") + 1] == python


def test_pip_is_not_given_the_flag(mocker, tmp_path):
    """pip always installs for the interpreter running it, and rejects the option outright."""
    python = str(tmp_path / "apps" / "Python312" / "python3.exe")

    command = _captured_command(mocker, python, uv_available=False)

    assert command[1:4] == ["-m", "pip", "install"]
    assert "--python" not in command


def test_a_python_resolved_by_name_is_left_for_uv_to_find(mocker):
    """Inside a virtual environment `find_python` returns a bare name, which would send uv looking
    down PATH again. Its own virtualenv detection is the better answer there."""
    command = _captured_command(mocker, "python3", uv_available=True)

    assert command[0] == "python3"
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
