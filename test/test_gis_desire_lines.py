import os
import pytest
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsProject, Qgis, QgsVectorLayer
from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog


def load_layers():
    path_to_gpkg = "test/data/SiouxFalls_project/SiouxFalls.gpkg"
    # append the layername part
    gpkg_links_layer = path_to_gpkg + "|layername=links"
    gpkg_nodes_layer = path_to_gpkg + "|layername=nodes"

    linkslayer = QgsVectorLayer(gpkg_links_layer, "Links layer", "ogr")
    nodeslayer = QgsVectorLayer(gpkg_nodes_layer, "Nodes layer", "ogr")

    if not linkslayer.isValid():
        print("Links layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(linkslayer)

    if not nodeslayer.isValid():
        print("Nodes layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(nodeslayer)


def test_click_create_without_layers(ae_with_project, qtbot):
    dialog = DesireLinesDialog(ae_with_project)
    dialog.show()
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)
    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.create_dl, Qt.LeftButton)
    assert len(exceptions) == 1


def test_click_create_with_layers(ae_with_project, qtbot, timeoutDetector):
    load_layers()
    dialog = DesireLinesDialog(ae_with_project)
    dialog.show()
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.create_dl, Qt.LeftButton)
    assert len(exceptions) == 0
    # default is delaunay
    assert dialog.progress_label.text() == "Building resulting layer"  # Last displayed line
    assert dialog.progressbar.value() == 61  # This number should match something in the SiouxFalls data
    # test that something cool happened on the map?


def test_click_create_with_layers_desired_selected(ae_with_project, qtbot, timeoutDetector):
    load_layers()
    dialog = DesireLinesDialog(ae_with_project)
    dialog.show()
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)
    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.radio_desire, Qt.LeftButton)
        qtbot.mouseClick(dialog.create_dl, Qt.LeftButton)
    assert len(exceptions) == 0
    assert dialog.progress_label.text() == "Creating Desire Lines"  # Last displayed line
    assert dialog.progressbar.value() == 275  # This number should match something in the SiouxFalls data
    # test that something cool happened on the map?


# Other than that, there isn't much error handling, so testing with wrong params triggers exceptions raising to the top
# For example, one would expect something like this:
@pytest.mark.skip(reason="Error handling implementation is required for this test")
def test_click_create_with_layers_with_wrong_id_param(ae_with_project, qtbot):
    load_layers()
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
