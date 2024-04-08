import pytest
from os.path import join, isfile
from os import remove

from qaequilibrae.modules.project_procedures.save_as_qgis import SaveAsQGZ


@pytest.fixture(scope="function")
def run_tsp(ae_with_project):
    from qaequilibrae.modules.routing_procedures.tsp_dialog import TSPDialog

    dialog = TSPDialog(ae_with_project)

    dialog.chb_block.setChecked(True)
    dialog.rdo_new_layer.setChecked(True)
    dialog.close_window = True
    dialog.cob_minimize.setCurrentText("distance")

    dialog.run()


def test_save_as_qgis(ae_with_project, tmpdir, mocker, load_layers_from_csv, run_tsp):

    file_path = f"{tmpdir}/text.qgz"
    function = "qaequilibrae.modules.project_procedures.save_as_qgis.SaveAsQGZ.choose_output"
    mocker.patch(function, return_value=file_path)

    # TODO: remove statement when test setups are merged
    lyr_file = "test/data/SiouxFalls_project/qgis_layers.sqlite"
    if isfile(lyr_file):
        remove(lyr_file)

    dialog = SaveAsQGZ(ae_with_project)

    assert isfile(join(dialog.qgis_project.project.project_base_path, "qgis_layers.sqlite"))

    assert isfile(file_path)

