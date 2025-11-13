import pytest
from qaequilibrae.modules.common_tools import GetOutputFileName

from qgis.PyQt.QtWidgets import QDialog


def test_get_file_name_cancelled(mocker):
    mocker.patch(
        "qaequilibrae.modules.common_tools.get_output_file_name.QFileDialog.exec_",
        return_value=False,
    )

    name, ext = GetOutputFileName(
        clss=QDialog(),
        box_name="Select file",
        file_types=[".txt"],
        default_type=".txt",
        start_path=".",
    )

    assert name is None
    assert ext is None


@pytest.mark.parametrize(
    ("filename", "exp_fname", "exp_ext"),
    [
        ("target.txt", "target.txt", "TXT"),
        ("filename.csv", "filename.csv", "CSV"),
        ("document..md", "document.md", "MD"),
        ("archive.zip", "archive.zip", "ZIP"),
        ("library.dyld", "library.dyld", "DYLD"),
    ],
)
def test_get_file_name_success(mocker, filename, exp_fname, exp_ext):
    mocker.patch(
        "qaequilibrae.modules.common_tools.get_output_file_name.QFileDialog.exec_",
        return_value=True,
    )
    mocker.patch(
        "qaequilibrae.modules.common_tools.get_output_file_name.QFileDialog.selectedFiles",
        return_value=[filename],
    )

    name, ext = GetOutputFileName(
        clss=QDialog(),
        box_name="Select file",
        file_types=[".txt"],
        default_type=".txt",
        start_path=".",
    )

    assert name == exp_fname
    assert ext == exp_ext