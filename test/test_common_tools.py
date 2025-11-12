import pytest
from qaequilibrae.modules.common_tools import GetOutputFileName

from qgis.PyQt.QtWidgets import QDialog


# TODO: test when it returns None and the correct file path
def test_get_file_name(mocker):
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
