import pytest
from qaequilibrae.modules.common_tools import GetOutputFileName, GetOutputFolderName

from qgis.PyQt.QtWidgets import QDialog


# def test_get_file_name_cancelled(mocker):
#     mocker.patch(
#         "qaequilibrae.modules.common_tools.get_output_file_name.QFileDialog.exec",
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
        "qaequilibrae.modules.common_tools.get_output_file_name.QFileDialog.exec",
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


def test_get_file_name_uses_and_updates_last_accessed_folder(mocker, tmp_path):
    last_folder = tmp_path / "last"
    selected_folder = tmp_path / "selected"
    fallback_folder = tmp_path / "fallback"
    last_folder.mkdir()
    selected_folder.mkdir()
    fallback_folder.mkdir()
    breadcrumb = tmp_path / "aequilibrae_last_folder.txt"
    breadcrumb.write_text(str(last_folder))

    mocker.patch(
        "qaequilibrae.modules.common_tools.get_output_file_name.tempfile.gettempdir",
        return_value=str(tmp_path),
    )
    set_directory = mocker.patch("qaequilibrae.modules.common_tools.get_output_file_name.QFileDialog.setDirectory")
    mocker.patch(
        "qaequilibrae.modules.common_tools.get_output_file_name.QFileDialog.exec",
        return_value=True,
    )
    mocker.patch(
        "qaequilibrae.modules.common_tools.get_output_file_name.QFileDialog.selectedFiles",
        return_value=[str(selected_folder / "target.txt")],
    )

    GetOutputFileName(
        clss=QDialog(),
        box_name="Select file",
        file_types=[".txt"],
        default_type=".txt",
        start_path=str(fallback_folder),
    )

    set_directory.assert_called_once_with(str(last_folder))
    assert breadcrumb.read_text() == str(selected_folder)


def test_get_output_folder_uses_and_updates_last_accessed_folder(mocker, tmp_path):
    last_folder = tmp_path / "last"
    selected_folder = tmp_path / "selected"
    fallback_folder = tmp_path / "fallback"
    last_folder.mkdir()
    selected_folder.mkdir()
    fallback_folder.mkdir()
    breadcrumb = tmp_path / "aequilibrae_last_folder.txt"
    breadcrumb.write_text(str(last_folder))

    mocker.patch(
        "qaequilibrae.modules.common_tools.get_output_file_name.tempfile.gettempdir",
        return_value=str(tmp_path),
    )
    get_folder = mocker.patch(
        "qaequilibrae.modules.common_tools.get_output_file_name.QFileDialog.getExistingDirectory",
        return_value=str(selected_folder),
    )

    assert GetOutputFolderName(str(fallback_folder), "Select folder") == str(selected_folder)

    assert get_folder.call_args.args[2] == str(last_folder)
    assert breadcrumb.read_text() == str(selected_folder)
