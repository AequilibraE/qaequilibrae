import os
import pytest
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsProject, Qgis, QgsVectorLayer
from qaequilibrae.modules.matrix_procedures.load_matrix_dialog import LoadMatrixDialog


def load_layers():
    # Add an Open Layer table
    path_to_gpkg = "test/data/SiouxFalls_project/SiouxFalls.gpkg"
    # append the layername part
    gpkg_links_layer = path_to_gpkg + "|layername=links"

    linkslayer = QgsVectorLayer(gpkg_links_layer, "Links layer", "ogr")

    if not linkslayer.isValid():
        print("Links layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(linkslayer)


def test_mat_menu(ae_with_project, qtbot):
    from qaequilibrae.modules.matrix_procedures.load_matrix_dialog import LoadMatrixDialog
    from test.test_qaequilibrae_menu_with_project import check_if_new_active_window_matches_class

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, LoadMatrixDialog)

    action = ae_with_project.menuActions["Data"][1]
    assert action.text() == "Import matrices", "Wrong text content"
    QTimer.singleShot(10, handle_trigger)
    action.trigger()
    messagebar = ae_with_project.iface.messageBar()
    assert len(messagebar.messages[3]) == 0, "Messagebar should be empty" + str(messagebar.messages)


def test_mat_load(ae_with_project, qtbot):
    load_layers()
    dialog = LoadMatrixDialog(ae_with_project)
    dialog.show()

    assert dialog.radio_layer_matrix.text() == "Open layer"

    qtbot.mouseClick(dialog.radio_layer_matrix, Qt.LeftButton)
    dialog.close()
    # qtbot.mouseClick(dialog.but_load, Qt.LeftButton)
    # qtbot.mouseClick(dialog.but_permanent_save, Qt.LeftButton)
