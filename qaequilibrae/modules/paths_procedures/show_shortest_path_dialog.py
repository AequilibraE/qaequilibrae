from os.path import dirname, join

import pandas as pd
from aequilibrae.context import get_logger
from aequilibrae.paths import Graph
from aequilibrae.paths.results import PathResults
from qgis.PyQt.QtCore import QEvent, QMetaType
from qgis.PyQt.QtGui import QColor
from qgis.core import QgsProject, QgsVectorLayer, QgsSpatialIndex, QgsField, QgsFeature
from qgis.gui import QgsVertexMarker
from qgis.utils import iface

from qaequilibrae.modules.common_tools import LoadGraphLayerSettingDialog, BaseDialog
from qaequilibrae.modules.common_tools import standard_path, geodataframe_from_layer
from qaequilibrae.modules.common_tools.writable_dataframe import make_writable_network_dataframe
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
        self.path = standard_path()
        self.node_id = None

        self.res = PathResults()
        self.link_features = None

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

        needed = {
            "link_id",
            "a_node",
            "b_node",
            "direction",
            self.mfield,
            f"{self.mfield}_ab",
            f"{self.mfield}_ba",
        }

        network = network[[c for c in network.columns if c in needed]]
        network = make_writable_network_dataframe(network)

        self.graph = Graph()
        self.graph.network = network
        self.graph.prepare_graph(self._centroids_from_model())

        if dlg2.remove_chosen_links:
            idx = self.line_layer.dataProvider().fieldNameIndex("link_id")
            remove = [feat.attributes()[idx] for feat in self.line_layer.selectedFeatures()]
            self.graph.exclude_links(remove)

        self.graph.set_graph(self.mfield)
        self.graph.set_skimming([self.mfield])
        self.graph.set_blocked_centroid_flows(dlg2.block_connector)

        self.res.prepare(self.graph)

        self.node_fields = [field.name() for field in self.node_layer.dataProvider().fields().toList()]
        self.index = QgsSpatialIndex()
        for feature in self.node_layer.getFeatures():
            self.index.addFeature(feature)
            self.node_keys[feature.id()] = feature.attributes()

        idx = self.line_layer.dataProvider().fieldNameIndex("link_id")
        self.link_features = {}
        for feat in self.line_layer.getFeatures():
            link_id = feat.attributes()[idx]
            self.link_features[link_id] = feat

        self.do_dist_matrix.setText(self.tr("Display"))
        self.set_picking_enabled(True)

    def clear_memory_layer(self):
        self.link_features = None

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
            self.res.reset()
            self.res.compute_path(int(self.path_from.text()), int(self.path_to.text()))

            if self.res.path is not None:
                # If you want to do selections instead of new layers
                if self.rdo_selection.isChecked():
                    self.create_path_with_selection()
                # If you want to create new layers
                else:
                    self.create_path_with_scratch_layer()
            else:
                msg = self.tr("No path between {} and {}").format(self.path_from.text(), self.path_to.text())
                self.qgis_project.iface_error_message(msg)

    def create_path_with_selection(self):
        f = "link_id"
        t = " or ".join([f"{f}={int(k)}" for k in self.res.path])
        self.line_layer.selectByExpression(t)

    def create_path_with_scratch_layer(self):
        crs = self.line_layer.dataProvider().crs().authid()
        vl = QgsVectorLayer(
            "LineString?crs={}".format(crs), f"{self.path_from.text()} to {self.path_to.text()}", "memory"
        )
        pr = vl.dataProvider()

        graph_fields = [
            QgsField("link_id", QMetaType.Type.LongLong),
            QgsField("a_node", QMetaType.Type.LongLong),
            QgsField("b_node", QMetaType.Type.LongLong),
            QgsField("direction", QMetaType.Type.Int),
        ]

        data = self.graph.graph.assign(__data_key__=self.graph.graph.link_id * self.graph.graph.direction)

        # Alongside the fields added above, the graph carries aequilibrae's own bookkeeping
        # columns, which mean nothing outside of it
        exclude = [
            "link_id",
            "a_node",
            "b_node",
            "direction",
            "__data_key__",
            "id",
            "__supernet_id__",
            "__compressed_id__",
        ]

        added_fields = [fld for fld in data if fld not in exclude]
        graph_fields.extend([QgsField(fld, QMetaType.Type.Double) for fld in added_fields])

        # add fields
        pr.addAttributes(graph_fields)
        vl.updateFields()  # tell the vector layer to fetch changes from the provider

        # add features
        all_links = []
        data = data[data["__data_key__"].isin(self.res.path * self.res.path_link_directions)]
        # The graph numbers its nodes by position, so they have to be translated back into the
        # node IDs the user knows
        all_nodes = self.graph.all_nodes
        for _, rec in data.iterrows():
            fet = self.link_features[int(rec.link_id)]
            # iterrows() types each row to hold every column at once, so an integer column comes
            # back as a NumPy float, and QGIS cannot write those into the fields declared above
            attrs = [
                int(rec.link_id),
                int(all_nodes[int(rec.a_node)]),
                int(all_nodes[int(rec.b_node)]),
                int(rec.direction),
            ]
            attrs.extend([float(rec[fld]) for fld in added_fields])

            feat = QgsFeature(vl.fields())
            feat.setGeometry(fet.geometry())
            feat.setAttributes(attrs)
            all_links.append(feat)

        # add all links to the temp layer
        pr.addFeatures(all_links)

        # add layer to the map
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

    def _centroids_from_model(self):
        with self.project.db_connection as conn:
            centroids = pd.read_sql("select node_id from nodes where is_centroid=1", con=conn).node_id.to_numpy()
            return centroids if centroids.size != 0 else None
