import pytest
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtWidgets import QApplication, QDialog

from qgis.core import QgsProject
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
    """The Configure button opens the graph settings dialog."""
    from qaequilibrae.modules.common_tools import LoadGraphLayerSettingDialog

    dialog = ShortestPathDialog(ae_with_project)
    dialog.show()
    qtbot.addWidget(dialog)
    qtbot.waitExposed(dialog)

    def handle_trigger():
        check_if_new_active_window_matches_class(qtbot, LoadGraphLayerSettingDialog, ShortestPathDialog)

    QTimer.singleShot(10, handle_trigger)
    qtbot.mouseClick(dialog.configure_graph, Qt.MouseButton.LeftButton)


# Graph preparation is intertwined with the LoadGraphLayerSettingDialog, so they cannot be tested independently
# TODO: for some reason, there is a segfault after this test is finished, couldn't find out why
def test_prepare_graph_and_network(ae_with_project, qtbot, timeoutDetector):
    """Loading a graph through the settings dialog is what brings the picking inputs to life."""
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
            assert dialog.do_dist_matrix.isEnabled() is True
            assert dialog.path_from.isEnabled() is True
            assert dialog.path_to.isEnabled() is True
            graph_dialog.close()

        QTimer.singleShot(10, handle_do_load_graph_trigger)
        qtbot.mouseClick(graph_dialog.do_load_graph, Qt.MouseButton.LeftButton)

    # Configuring is the only thing on offer until there is a graph
    assert dialog.do_dist_matrix.isEnabled() is False
    assert dialog.path_from.isEnabled() is False
    assert dialog.path_to.isEnabled() is False
    assert dialog.configure_graph.isEnabled() is True
    QTimer.singleShot(10, handle_configure_graph_trigger)
    qtbot.mouseClick(dialog.configure_graph, Qt.MouseButton.LeftButton)


def test_links_layer_is_loaded_when_it_is_not_on_the_canvas(ae_with_project):
    """Everything the dialog offers is done against the network on screen."""
    assert not QgsProject.instance().mapLayersByName("links"), "the fixture starts without it"

    dialog = ShortestPathDialog(ae_with_project)

    assert QgsProject.instance().mapLayersByName("links")
    assert dialog.line_layer.id() in QgsProject.instance().mapLayers()

    dialog.close()


def test_a_links_layer_already_on_the_canvas_is_reused(ae_with_project):
    """A links layer already on the map is picked up rather than added a second time."""
    ae_with_project.load_layer_by_name("links")
    already_there = QgsProject.instance().mapLayersByName("links")[0]

    dialog = ShortestPathDialog(ae_with_project)

    assert dialog.line_layer is already_there
    assert len(QgsProject.instance().mapLayersByName("links")) == 1, "a second copy was added"

    dialog.close()


def test_links_layer_removed_from_the_canvas_is_put_back(ae_with_project):
    """The panel rebuilds a removed layer in memory, but that replacement is not on the map."""
    ae_with_project.load_layer_by_name("links")
    QgsProject.instance().removeMapLayer(QgsProject.instance().mapLayersByName("links")[0])
    assert not QgsProject.instance().mapLayersByName("links")

    dialog = ShortestPathDialog(ae_with_project)

    assert dialog.line_layer.id() in QgsProject.instance().mapLayers()

    dialog.close()


@pytest.fixture
def mock_load_graph_layer_setting_dialog(mocker):
    """Mock patch for LoadGraphLayerSettingDialog."""
    mock_dialog = mocker.Mock(spec=QDialog)
    mock_dialog.remove_chosen_links = True
    mock_dialog.error = []
    mock_dialog.mode = "c"
    mock_dialog.minimize_field = "distance"
    mock_dialog.block_connector = False

    mocker.patch(
        "qaequilibrae.modules.paths_procedures.show_shortest_path_dialog.LoadGraphLayerSettingDialog",
        return_value=mock_dialog,
    )

    return mock_dialog


def test_shortest_path_dialog(ae_with_project, mock_load_graph_layer_setting_dialog):
    """A path between two typed node IDs lands in a new layer, with the selected links left out."""
    ae_with_project.load_layer_by_name("links")

    layer = QgsProject.instance().mapLayersByName("links")[0]
    ae_with_project.iface.setActiveLayer(layer)
    exp = '"link_id" IN (4, 14)'
    layer.selectByExpression(exp)

    dialog = ShortestPathDialog(ae_with_project)
    dialog.prepare_graph_and_network()
    dialog.path_from.setText("1")
    dialog.path_to.setText("6")
    dialog.rdo_selection.setChecked(False)
    dialog.produces_path()

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert "1 to 6" in prj_layers

    path = QgsProject.instance().mapLayersByName("1 to 6")[0]
    assert path.featureCount() == 4

    dialog.close()


def test_map_clicks_alternate_between_the_boxes(ae_with_project, mock_load_graph_layer_setting_dialog):
    """Two clicks on the map fill From then To, each leaving a marker of its own behind."""
    from qgis.core import QgsPointXY

    ae_with_project.load_layer_by_name("links")

    dialog = ShortestPathDialog(ae_with_project)
    dialog.prepare_graph_and_network()

    # Configuring the graph puts the canvas in picking mode, aimed at From
    assert ae_with_project.iface.mapCanvas().mapTool() is dialog.clickTool
    assert dialog.fill_target == "from"

    nodes = {feat["node_id"]: feat.geometry().asPoint() for feat in dialog.node_layer.getFeatures()}

    def click_on(node_id):
        point = nodes[node_id]
        dialog.clickTool.point = QgsPointXY(point.x(), point.y())
        dialog.clickTool.signal.emit(1)

    click_on(1)
    assert dialog.path_from.text() == "1"
    assert dialog.path_to.text() == ""
    assert dialog.fill_target == "to", "the next click should have been aimed at To"

    click_on(6)
    assert dialog.path_from.text() == "1"
    assert dialog.path_to.text() == "6"
    assert dialog.fill_target == "from", "the boxes should alternate"

    # One marker per end, told apart by colour and sitting on the nodes that were picked
    assert set(dialog.node_markers) == {"from", "to"}
    assert dialog.node_markers["from"].color() != dialog.node_markers["to"].color()
    assert dialog.node_markers["from"].center() == nodes[1]
    assert dialog.node_markers["to"].center() == nodes[6]

    # A third click goes back to From, and moves that marker rather than adding one
    from_marker = dialog.node_markers["from"]
    click_on(10)
    assert dialog.path_from.text() == "10"
    assert dialog.node_markers["from"] is from_marker

    dialog.close()

    # Closing gives the canvas back and takes the markers off it
    assert ae_with_project.iface.mapCanvas().mapTool() is not dialog.clickTool
    assert dialog.node_markers == {}


def test_clicking_a_box_aims_the_next_map_click_at_it(ae_with_project, mock_load_graph_layer_setting_dialog):
    """Choosing a box by hand overrides the alternation."""
    from qgis.PyQt.QtCore import QCoreApplication, QEvent
    from qgis.PyQt.QtGui import QFocusEvent

    ae_with_project.load_layer_by_name("links")

    dialog = ShortestPathDialog(ae_with_project)
    dialog.prepare_graph_and_network()
    assert dialog.fill_target == "from"

    # setFocus() does nothing while the dialog is not shown, and calling event() directly would
    # skip the filter entirely - only sendEvent() runs an event past the installed filters
    QCoreApplication.sendEvent(dialog.path_to, QFocusEvent(QEvent.Type.FocusIn))
    assert dialog.fill_target == "to"

    QCoreApplication.sendEvent(dialog.path_from, QFocusEvent(QEvent.Type.FocusIn))
    assert dialog.fill_target == "from"

    dialog.close()


def test_cancelling_the_configuration_leaves_the_dialog_as_it_was(
    ae_with_project, mock_load_graph_layer_setting_dialog
):
    """Giving up partway must not leave the inputs greyed out under a "Loading data" button."""
    ae_with_project.load_layer_by_name("links")

    dialog = ShortestPathDialog(ae_with_project)

    # Cancelled before ever configuring: everything stays out of reach, and the button goes
    # back to its own label rather than being stuck on "Loading data"
    mock_load_graph_layer_setting_dialog.mode = ""
    dialog.prepare_graph_and_network()
    assert dialog.path_from.isEnabled() is False
    assert dialog.do_dist_matrix.isEnabled() is False
    assert dialog.do_dist_matrix.text() == "Compute"

    # Configured once, then cancelled out of a second attempt: the working state survives
    mock_load_graph_layer_setting_dialog.mode = "c"
    dialog.prepare_graph_and_network()
    assert dialog.path_from.isEnabled() is True
    assert dialog.do_dist_matrix.text() == "Display"

    mock_load_graph_layer_setting_dialog.mode = ""
    dialog.prepare_graph_and_network()
    assert dialog.path_from.isEnabled() is True
    assert dialog.path_to.isEnabled() is True
    assert dialog.do_dist_matrix.isEnabled() is True
    assert dialog.do_dist_matrix.text() == "Display"
    assert ae_with_project.iface.mapCanvas().mapTool() is dialog.clickTool

    dialog.close()


def test_escape_still_gives_the_canvas_back(ae_with_project, mock_load_graph_layer_setting_dialog):
    """Escape goes straight to reject(), so it never delivers a close event to clean up in."""
    ae_with_project.load_layer_by_name("links")

    dialog = ShortestPathDialog(ae_with_project)
    dialog.prepare_graph_and_network()
    dialog.mark_node("from", next(dialog.node_layer.getFeatures()).geometry().asPoint())

    assert ae_with_project.iface.mapCanvas().mapTool() is dialog.clickTool
    assert dialog.node_markers

    dialog.reject()

    assert ae_with_project.iface.mapCanvas().mapTool() is not dialog.clickTool
    assert dialog.node_markers == {}
