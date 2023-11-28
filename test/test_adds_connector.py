import pytest
import threading

from qaequilibrae.modules.network.adds_connectors_dialog import AddConnectorsDialog


def test_add_connectors(ae_with_project, qtbot):
    dialog = AddConnectorsDialog(ae_with_project)
    
    dialog.run()