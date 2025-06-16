from qgis.PyQt.QtCore import Qt
from qaequilibrae.modules.paths_procedures.isochrones_dialog import IsochronesDialog


def test_init(ae_with_project, qtbot, timeoutDetector):
    dialog = IsochronesDialog(ae_with_project)

    dialog.cob_minimizing.setCurrentText("distance")
    dialog.cob_skim.setCurrentText("distance")
    dialog.block_paths.setChecked(False)
    dialog.cob_layer.setCurrentText("nodes")
    dialog.line_start_id.setText("1")

    qtbot.mouseClick(dialog.but_plot, Qt.LeftButton)
