import pytest
from qaequilibrae.modules.common_tools import GetOutputFileName

from qgis.PyQt.QtWidgets import QDialog


# def test_get_file_name_cancelled(mocker):
#     mocker.patch(
#         "qaequilibrae.modules.common_tools.get_output_file_name.QFileDialog.exec_",
#         return_value=False,
#     )

#     name, ext = GetOutputFileName(
#         clss=QDialog(),
#         box_name="Select file",
#         file_types=[".txt"],
#         default_type=".txt",
#         start_path=".",
#     )

#     assert name is None
#     assert ext is None


@pytest.mark.parametrize(
    ("is_filename_chosen", "filename", "exp_fname", "exp_ext"),
    [
        (True, "target.txt", "target.txt", "TXT"),
        (True, "document..md", "document.md", "MD"),
        (True, "library.dyld", "library.dyld", "DYLD"),
        (False, "target.txt", "target.txt", "TXT"),
    ],
)
def test_get_file_name(mocker, is_filename_chosen, filename, exp_fname, exp_ext):
    mocker.patch(
        "qaequilibrae.modules.common_tools.get_output_file_name.QFileDialog.exec_",
        return_value=is_filename_chosen,
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

    if is_filename_chosen:
        assert name == exp_fname
        assert ext == exp_ext
    else:
        assert name is None
        assert ext is None
