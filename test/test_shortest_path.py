from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication

from qaequilibrae.modules.paths_procedures.show_shortest_path_dialog import ShortestPathDialog


def wait_for_active_window(qtbot, previousClass):
    timeout = 3000
    window = QApplication.activeWindow()
    while (window is None or isinstance(window, previousClass)) and timeout > 0:
        window = QApplication.activeWindow()
        qtbot.wait(100)
        timeout -= 100
    assert timeout > 0, "Waiting for window to open timed out after 3 seconds"
    return window


def check_if_new_active_window_matches_class(qtbot, windowClass, previousClass):
    dialog = wait_for_active_window(qtbot, previousClass)
    try:
        assert isinstance(dialog, windowClass), "Active window does not match the correct window class"
    finally:
        dialog.close()
        assert QApplication.activeWindow() is None, "Dialog window did not close properly"


def test_click_configure_graph(ae_with_project, qtbot, timeoutDetector):
    from qaequilibrae.modules.common_tools import LoadGraphLayerSettingDialog

    dialog = ShortestPathDialog(ae_with_project)
    dialog.show()
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, LoadGraphLayerSettingDialog, ShortestPathDialog)

    QTimer.singleShot(10, handle_trigger)
    qtbot.mouseClick(dialog.configure_graph, Qt.LeftButton)


# Graph preparation is intertwined with the LoadGraphLayerSettingDialog, so they cannot be tested independently
# TODO: for some reason, there is a segfault after this test is finished, couldn't find out why
def test_prepare_graph_and_network(ae_with_project, qtbot, timeoutDetector):
    from qaequilibrae.modules.common_tools import LoadGraphLayerSettingDialog

    dialog = ShortestPathDialog(ae_with_project)
    dialog.show()
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    def handle_configure_graph_trigger():
        global graph_dialog
        graph_dialog = wait_for_active_window(qtbot, ShortestPathDialog)

        def handle_do_load_graph_trigger():
            global graph_dialog
            assert graph_dialog.isVisible() is False, "Dialog did not close properly"
            assert dialog.from_but.isEnabled() is True
            assert dialog.to_but.isEnabled() is True
            graph_dialog.close()

        QTimer.singleShot(10, handle_do_load_graph_trigger)
        qtbot.mouseClick(graph_dialog.do_load_graph, Qt.LeftButton)

    assert dialog.from_but.isEnabled() is False
    assert dialog.to_but.isEnabled() is False
    QTimer.singleShot(10, handle_configure_graph_trigger)
    qtbot.mouseClick(dialog.configure_graph, Qt.LeftButton)
