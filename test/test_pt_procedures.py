import os
import pytest
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication
from qgis.core import QgsProject, Qgis, QgsVectorLayer
from qaequilibrae.modules.public_transport_procedures.gtfs_feed import GTFSFeed
from qaequilibrae.modules.public_transport_procedures.gtfs_importer import GTFSImporter


def test_click(ae_with_project, qtbot):
    dialog = GTFSImporter(ae_with_project)
    dialog.show()

    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)
    with qtbot.capture_exceptions() as exceptions:
        qtbot.mouseClick(dialog.create_dl, Qt.LeftButton)
    assert len(exceptions) == 1
