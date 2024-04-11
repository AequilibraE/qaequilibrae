import pytest
from qaequilibrae.modules.matrix_procedures.display_aequilibrae_formats_dialog import DisplayAequilibraEFormatsDialog


# TODO:
def test_display_data_without_project(ae, mocker):
    dialog = DisplayAequilibraEFormatsDialog(ae)

    function = "qaequilibrae.modules.matrix_procedures.display_aequilibrae_formats_dialog.DisplayAequilibraEFormatsDialog.get_file_name"
    mocker.patch(function, return_value=(None, None))

    messagebar = ae.iface.messageBar()
    assert messagebar.messages[1][-1] == "Error::Path provided is not a valid dataset", "Level 1 error message is missing"

# @pytest.mark.skip("")
def test_display_data_with_project(ae_with_project, mocker):
    function = "qaequilibrae.modules.matrix_procedures.display_aequilibrae_formats_dialog.DisplayAequilibraEFormatsDialog.get_file_name"
    mocker.patch(function, return_value=("test/data/SiouxFalls_project/matrices/demand.aem", "AEM"))

    dialog = DisplayAequilibraEFormatsDialog(ae_with_project)

    print(dialog.__dict__)