from os.path import dirname, join

import pandas as pd
from aequilibrae.context import get_logger
from qgis.PyQt.QtCore import QEvent
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingUtils,
    QgsProject,
    QgsSpatialIndex,
)
from qgis.gui import QgsVertexMarker
from qgis.utils import iface

from qaequilibrae.modules.common_tools import LoadGraphLayerSettingDialog, BaseDialog
from qaequilibrae.modules.common_tools import geodataframe_from_layer
from qaequilibrae.modules.paths_procedures.point_tool import PointTool

logger = get_logger()

# Shape and colour telling the two ends of the path apart on the map
MARKER_STYLES = {
    "from": (QgsVertexMarker.IconType.ICON_CIRCLE, QColor(0, 160, 60)),
    "to": (QgsVertexMarker.IconType.ICON_BOX, QColor(200, 30, 30)),
}


class ShortestPathDialog(BaseDialog):
    def __init__(self, qgis_project):
        super().__init__(
            ui_file=join(dirname(__file__), "forms/ui_compute_path.ui"),
            qgis_project=qgis_project,
            # Parented to the QGIS window so that clicking the map raises the main window with
            # this dialog still in front of it, instead of burying it
            parent=iface.mainWindow(),
        )

    def _base_ui_setup(self):
        self.field_types = {}
        self.centroids = None
        self.node_layer = self.qgis_project.layers["nodes"][0]
        self.line_layer = self._links_layer_on_canvas()
        self.node_keys = {}
        self.node_fields = None
        self.index = None
        self.matrix = None
        self.node_id = None

        # Which box the next click on the map lands in, and the markers showing where the two
        # ends currently sit
        self.fill_target = "from"
        self.node_markers = {}
        self.previous_map_tool = None

        self.clickTool = PointTool(self.iface.mapCanvas())
        self.clickTool.signal.connect(self.node_picked)

        # Clicking into a box aims the next map click at it, overriding the alternation
        self.path_from.installEventFilter(self)
        self.path_to.installEventFilter(self)

        self.set_picking_enabled(False)
        self.configure_graph.clicked.connect(self.prepare_graph_and_network)
        self.do_dist_matrix.clicked.connect(self.produces_path)
        self.finished.connect(self.give_canvas_back)

    def set_picking_enabled(self, enabled: bool):
        """Nothing that needs a graph behind it is within reach until there is one.

        Configuring is the only thing on offer to begin with, so the boxes and the compute
        button stay greyed out, and the canvas is only taken over once picking can resolve
        a click into a node.
        """
        self.path_from.setEnabled(enabled)
        self.path_to.setEnabled(enabled)
        self.do_dist_matrix.setEnabled(enabled)
        if enabled:
            self.activate_map_tool()
        else:
            self.release_map_tool()

    def abandon_configuration(self, was_ready: bool, previous_text: str):
        """Puts the dialog back as it was when a configuration is given up on partway."""
        self.do_dist_matrix.setText(previous_text)
        self.set_picking_enabled(was_ready)

    def prepare_graph_and_network(self):
        # Captured so that cancelling out of the configuration leaves a dialog that had already
        # been configured exactly as it was, rather than greyed out and reading "Loading data"
        was_ready = self.do_dist_matrix.isEnabled()
        previous_text = self.do_dist_matrix.text()

        self.do_dist_matrix.setText(self.tr("Loading data"))
        self.set_picking_enabled(False)

        with self.project.db_connection as conn:
            all_modes = pd.read_sql("select mode_name, mode_id from modes", conn)

        network = geodataframe_from_layer(self.line_layer)
        if "modes" not in network.columns:
            raise ValueError("Your network does not have mode information")

        numeric_fields = network.select_dtypes(include=["number"]).columns.tolist()

        dlg2 = LoadGraphLayerSettingDialog(self.qgis_project, all_modes, numeric_fields)
        dlg2.show()
        dlg2.exec()

        if len(dlg2.error) > 0 or len(dlg2.mode) <= 0:
            return self.abandon_configuration(was_ready, previous_text)

        self.mode = dlg2.mode
        self.mfield = dlg2.minimize_field.lower()

        mode_mask = network["modes"].str.contains(str(self.mode), na=False, regex=False)
        network = network.loc[mode_mask].copy(deep=True).infer_objects()

        if network.shape[0] == 0:
            # self.project is the AequilibraE project, which has no message bar of its own
            self.qgis_project.iface_error_message(self.tr("No link with the mode you are interested in"))
            return self.abandon_configuration(was_ready, previous_text)

        self.block_connector = dlg2.block_connector
        self.remove_chosen_links = dlg2.remove_chosen_links

        self.node_fields = [field.name() for field in self.node_layer.dataProvider().fields().toList()]
        self.index = QgsSpatialIndex()
        for feature in self.node_layer.getFeatures():
            self.index.addFeature(feature)
            self.node_keys[feature.id()] = feature.attributes()

        self.do_dist_matrix.setText(self.tr("Display"))
        self.set_picking_enabled(True)

    def activate_map_tool(self):
        """Hands the canvas over to the point tool, so the map is ready to be clicked."""
        canvas = self.iface.mapCanvas()
        if canvas.mapTool() is not self.clickTool:
            self.previous_map_tool = canvas.mapTool()
        canvas.setMapTool(self.clickTool)
        self.fill_target = "from"

    def release_map_tool(self):
        """Gives the canvas back whatever tool was in use before this dialog took it."""
        canvas = self.iface.mapCanvas()
        if canvas.mapTool() is self.clickTool:
            if self.previous_map_tool is None:
                canvas.unsetMapTool(self.clickTool)
            else:
                canvas.setMapTool(self.previous_map_tool)
        self.previous_map_tool = None

    def eventFilter(self, obj, event):
        """Picking a box by hand decides where the next click on the map goes."""
        if event.type() == QEvent.Type.FocusIn:
            if obj is self.path_from:
                self.fill_target = "from"
            elif obj is self.path_to:
                self.fill_target = "to"
        return super().eventFilter(obj, event)

    def node_picked(self):
        """Fills the box the click was aimed at, then aims the next one at the other box."""
        node_id, point = self.find_point()
        if node_id is None:
            return

        target = self.fill_target
        box = self.path_from if target == "from" else self.path_to
        box.setText(str(node_id))
        self.mark_node(target, point)

        self.fill_target = "to" if target == "from" else "from"

    def mark_node(self, target, point):
        """Shows where an end of the path sits, well before anything is computed."""
        marker = self.node_markers.get(target)
        if marker is None:
            icon_type, color = MARKER_STYLES[target]
            marker = QgsVertexMarker(self.iface.mapCanvas())
            marker.setIconType(icon_type)
            marker.setColor(color)
            marker.setFillColor(color)
            marker.setIconSize(14)
            marker.setPenWidth(3)
            self.node_markers[target] = marker
        marker.setCenter(point)

    def clear_markers(self):
        scene = self.iface.mapCanvas().scene()
        for marker in self.node_markers.values():
            scene.removeItem(marker)
        self.node_markers.clear()

    def find_point(self):
        """Returns the (node_id, position) of the model node closest to the last click."""
        try:
            nearest = self.index.nearestNeighbor(self.clickTool.point, 1)
            if not nearest:
                return None, None

            feature_id = nearest[0]
            node_id = self.node_keys[feature_id][self.node_fields.index("node_id")]
            geometry = self.node_layer.getFeature(feature_id).geometry()
            return node_id, geometry.asPoint()
        except Exception as e:
            logger.error(e.args)
            return None, None

    def produces_path(self):
        if self.path_from.text().isdigit() and self.path_to.text().isdigit():
            selected_links = []
            if self.remove_chosen_links:
                idx = self.line_layer.dataProvider().fieldNameIndex("link_id")
                selected_links = [feat.attributes()[idx] for feat in self.line_layer.selectedFeatures()]

            from qaequilibrae.modules.processing_provider.paths_procedures.shortest_path import ShortestPath

            context = QgsProcessingContext()
            context.setProject(QgsProject.instance())
            parameters = {
                ShortestPath.LINKS: self.line_layer,
                ShortestPath.MODE: str(self.mode),
                ShortestPath.COST_FIELD: self.mfield,
                ShortestPath.FROM_NODE: int(self.path_from.text()),
                ShortestPath.TO_NODE: int(self.path_to.text()),
                ShortestPath.BLOCK_CENTROID_FLOWS: self.block_connector,
                ShortestPath.EXCLUDED_LINKS: ",".join(str(link_id) for link_id in selected_links),
                ShortestPath.OUTPUT: "TEMPORARY_OUTPUT",
            }
            if self.block_connector:
                parameters[ShortestPath.NODES] = self.node_layer

            try:
                algorithm = ShortestPath()
                algorithm.initAlgorithm()
                result, succeeded = algorithm.run(parameters, context, QgsProcessingFeedback())
                if not succeeded:
                    return
            except QgsProcessingException as exception:
                self.qgis_project.iface_error_message(str(exception))
                return

            path = [int(link_id) for link_id in result[ShortestPath.PATH_LINKS].split(",") if link_id]
            if self.rdo_selection.isChecked():
                self.create_path_with_selection(path)
            else:
                self.create_path_with_scratch_layer(result[ShortestPath.OUTPUT], context)

    def create_path_with_selection(self, path):
        f = "link_id"
        t = " or ".join([f"{f}={int(k)}" for k in path])
        self.line_layer.selectByExpression(t)

    def create_path_with_scratch_layer(self, destination, context):
        vl = context.takeResultLayer(destination)
        if vl is None:
            vl = QgsProcessingUtils.mapLayerFromString(destination, context)
        if vl is None:
            self.qgis_project.iface_error_message(self.tr("The shortest path output could not be loaded"))
            return

        vl.setName(f"{self.path_from.text()} to {self.path_to.text()}")
        QgsProject.instance().addMapLayer(vl)
        symbol = vl.renderer().symbol()
        symbol.setWidth(1)
        self.iface.mapCanvas().refresh()

    def exit_procedure(self):
        self.close()

    def closeEvent(self, event):
        self.give_canvas_back()
        super().closeEvent(event)

    def give_canvas_back(self):
        """The map tool and the markers live on the canvas, so they outlive this dialog unless
        they are taken down on the way out"""
        self.release_map_tool()
        self.clear_markers()

    def _links_layer_on_canvas(self):
        """Returns the links layer, putting it on the map first if it is not there already."""
        layer = self._loaded_links_layer()
        if layer is not None:
            return layer

        self.qgis_project.load_layer_by_name("links")
        return self.qgis_project.layers["links"][0]

    def _loaded_links_layer(self):
        if "links" not in self.qgis_project.layers:
            return None
        layer = self.qgis_project.layers["links"][0]
        if layer.id() in QgsProject.instance().mapLayers():
            return layer
        return None
