from PyQt5.QtCore import Qt, QTimer
from qgis.core import QgsProject, QgsVectorLayer
from qaequilibrae.modules.matrix_procedures.load_matrix_dialog import LoadMatrixDialog


def load_layers():
    path_to_gpkg = 'file:test/data/SiouxFalls_project/aon.csv?delimiter=,'
    datalayer = QgsVectorLayer(path_to_gpkg, "open_layer", "delimitedtext")

    if not datalayer.isValid():
        print("Open layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(datalayer)


def test_matrix_menu(ae_with_project, qtbot):
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


def test_save_matrix(ae_with_project, qtbot):
    load_layers()
    dialog = LoadMatrixDialog(ae_with_project)
    dialog.show()

    qtbot.mouseClick(dialog.but_load, Qt.LeftButton)
    qtbot.mouseClick(dialog.but_permanent_save, Qt.LeftButton)
    dialog.close()
