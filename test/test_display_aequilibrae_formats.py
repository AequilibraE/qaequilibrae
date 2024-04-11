import os
import numpy as np
import pytest

from qaequilibrae.modules.matrix_procedures.display_aequilibrae_formats_dialog import DisplayAequilibraEFormatsDialog


def test_display_data_no_path(ae, mocker):
    function = "qaequilibrae.modules.matrix_procedures.display_aequilibrae_formats_dialog.DisplayAequilibraEFormatsDialog.get_file_name"
    mocker.patch(function, return_value=(None, None))

    dialog = DisplayAequilibraEFormatsDialog(ae)
    dialog.close()

    messagebar = ae.iface.messageBar()
    assert (
        messagebar.messages[1][-1] == "Error::Path provided is not a valid dataset"
    ), "Level 1 error message is missing"


@pytest.mark.parametrize("has_project", [True, False])
@pytest.mark.parametrize("file_name", ("demand.aem", "SiouxFalls.omx"))
def test_display_data_with_path(tmpdir, ae_with_project, mocker, has_project, file_name):
    file_path = f"test/data/SiouxFalls_project/matrices/{file_name}"
    name, extension = file_name.split(".")
    file_func = "qaequilibrae.modules.matrix_procedures.display_aequilibrae_formats_dialog.DisplayAequilibraEFormatsDialog.get_file_name"
    mocker.patch(file_func, return_value=(file_path, extension.upper()))

    out_func = "qaequilibrae.modules.matrix_procedures.display_aequilibrae_formats_dialog.DisplayAequilibraEFormatsDialog.csv_file_path"
    mocker.patch(out_func, return_value=f"{tmpdir}/{name}.csv")

    dialog = DisplayAequilibraEFormatsDialog(ae_with_project, file_path, has_project)
    dialog.export()
    dialog.exit_procedure()

    assert dialog.error is None
    assert np.sum(dialog.data_to_show.__dict__["matrix"]["matrix"]) == 360600
    assert "matrix" in dialog.list_cores
    assert "taz" in dialog.list_indices
    assert dialog.data_type == extension.upper()
    assert os.path.isfile(f"{tmpdir}/{name}.csv")
