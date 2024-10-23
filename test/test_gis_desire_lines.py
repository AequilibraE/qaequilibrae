import pytest
from PyQt5.QtCore import Qt
from qgis.core import QgsProject

from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog


def test_click_create_without_layers(ae_with_project, qtbot):
    dialog = DesireLinesDialog(ae_with_project)
    dialog.show()
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)
    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.create_dl, Qt.LeftButton)
    assert len(exceptions) == 0

    messagebar = ae_with_project.iface.messageBar()
    assert (
        messagebar.messages[1][0]
        == "Inputs not loaded properly:You need the layer and at least one matrix_procedures core"
    ), "Level 1 error message is missing"


@pytest.mark.parametrize("load_sfalls_from_layer", [None], indirect=True)
def test_click_create_with_layers(ae_with_project, qtbot, timeoutDetector, load_sfalls_from_layer):
    dialog = DesireLinesDialog(ae_with_project)
    dialog.show()
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.create_dl, Qt.LeftButton)
    assert len(exceptions) == 0
    # default is delaunay
    assert dialog.progress_label.text() == "Building resulting layer"  # Last displayed line
    assert dialog.progressbar.value() == 62  # This number should match the number of edges in the SiouxFalls data
    # test that something cool happened on the map?


@pytest.mark.parametrize("load_sfalls_from_layer", [None], indirect=True)
def test_click_create_with_layers_desired_selected(ae_with_project, qtbot, timeoutDetector, load_sfalls_from_layer):
    dialog = DesireLinesDialog(ae_with_project)
    dialog.show()
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)
    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.radio_desire, Qt.LeftButton)
        qtbot.mouseClick(dialog.create_dl, Qt.LeftButton)
    assert len(exceptions) == 0
    assert dialog.progress_label.text() == "Creating Desire Lines"  # Last displayed line
    assert dialog.progressbar.value() == 276  # This number should match the number of edges in the SiouxFalls data
    # test that something cool happened on the map?


# Other than that, there isn't much error handling, so testing with wrong params triggers exceptions raising to the top
# For example, one would expect something like this:
@pytest.mark.skip(reason="Error handling implementation is required for this test")
@pytest.mark.parametrize("load_sfalls_from_layer", [None], indirect=True)
def test_click_create_with_layers_with_wrong_id_param(ae_with_project, qtbot, load_sfalls_from_layer):
    dialog = DesireLinesDialog(ae_with_project)
    dialog.show()
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)
    # set "y" as id field, which is incorrect
    dialog.zone_id_field.setCurrentIndex(3)
    with qtbot.capture_exceptions() as exceptions:
        # this shouldn't hang, but it does
        qtbot.mouseClick(dialog.create_dl, Qt.LeftButton)
    assert len(exceptions) == 0, "Exception shouldn't be raised all the way to here"
    assert dialog.progress_label.text() == "Some error message saying id field is incorrect"
