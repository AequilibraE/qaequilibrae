from os.path import dirname, join

import pandas as pd
from aequilibrae.context import get_logger
from aequilibrae.paths import Graph
from aequilibrae.paths.results import PathResults
from qgis.PyQt import QtCore
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsProject, QgsVectorLayer, QgsSpatialIndex, QgsField, QgsFeature
from qgis.utils import iface

from qaequilibrae.modules.common_tools import LoadGraphLayerSettingDialog, BaseDialog
from qaequilibrae.modules.common_tools import standard_path, geodataframe_from_layer
from qaequilibrae.modules.paths_procedures.point_tool import PointTool

logger = get_logger()


class ShortestPathDialog(BaseDialog):
    clickTool = PointTool(iface.mapCanvas())

    def __init__(self, qgis_project):
        super().__init__(
            ui_file=join(dirname(__file__), "forms/ui_compute_path.ui"),
            qgis_project=qgis_project,
        )

    def _base_ui_setup(self):
        self.field_types = {}
        self.centroids = None
        self.node_layer = self.qgis_project.layers["nodes"][0]
        self.line_layer = self.qgis_project.layers["links"][0]
        self.node_keys = {}
        self.node_fields = None
        self.index = None
        self.matrix = None
        self.path = standard_path()
        self.node_id = None

        self.res = PathResults()
        self.link_features = None

        self.do_dist_matrix.setEnabled(False)
        self.from_but.setEnabled(False)
        self.to_but.setEnabled(False)
        self.configure_graph.clicked.connect(self.prepare_graph_and_network)
        self.from_but.clicked.connect(self.search_for_point_from)
        self.to_but.clicked.connect(self.search_for_point_to)
        self.do_dist_matrix.clicked.connect(self.produces_path)

    def prepare_graph_and_network(self):
        self.do_dist_matrix.setText(self.tr("Loading data"))
        self.from_but.setEnabled(False)
        self.to_but.setEnabled(False)

        with self.project.db_connection as conn:
            all_modes = pd.read_sql("select mode_name, mode_id from modes", conn)

        network = geodataframe_from_layer(self.line_layer)
        if "modes" not in network.columns:
            raise ValueError("Your network does not have mode information")

        numeric_fields = network.select_dtypes(include=['number']).columns.tolist()

        dlg2 = LoadGraphLayerSettingDialog(self.qgis_project, all_modes, numeric_fields)
        dlg2.show()
        dlg2.exec_()

        if len(dlg2.error) > 0 or len(dlg2.mode) <= 0:
            return

        self.mode = dlg2.mode
        self.minimize_field = dlg2.minimize_field.lower()

        mode_mask = network["modes"].astype(str).str.contains(str(self.mode), na=False)
        network = network[mode_mask]

        if network.shape[0] == 0:
            self.project.iface_error_message("No link with the mode you are interested in")
            return None

        self.graph = Graph()
        self.graph.network = network
        self.graph.prepare_graph(self._centroids_from_model())

        if dlg2.remove_chosen_links:
            idx = self.line_layer.dataProvider().fieldNameIndex("link_id")
            remove = [feat.attributes()[idx] for feat in self.line_layer.selectedFeatures()]
            self.graph.exclude_links(remove)

        self.graph.set_graph(self.minimize_field)
        self.graph.set_skimming([self.minimize_field])
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
        self.do_dist_matrix.setEnabled(True)
        self.from_but.setEnabled(True)
        self.to_but.setEnabled(True)

    def clear_memory_layer(self):
        self.link_features = None

    def search_for_point_from(self):
        self.clickTool.signal.connect(self.fill_path_from)
        self.iface.mapCanvas().setMapTool(self.clickTool)
        self.from_but.setEnabled(False)

    def search_for_point_to(self):
        self.iface.mapCanvas().setMapTool(self.clickTool)
        self.clickTool.signal.connect(self.fill_path_to)
        self.to_but.setEnabled(False)

    def search_for_point_to_after_from(self):
        self.iface.mapCanvas().setMapTool(self.clickTool)
        self.clickTool.signal.connect(self.fill_path_to)

    def fill_path_to(self):
        self.to_node = self.find_point()
        self.path_to.setText(str(self.to_node))
        self.to_but.setEnabled(True)

    @QtCore.pyqtSlot()
    def fill_path_from(self):
        self.from_node = self.find_point()
        self.path_from.setText(str(self.from_node))
        self.from_but.setEnabled(True)
        self.search_for_point_to_after_from()

    def find_point(self):
        try:
            point = self.clickTool.point
            nearest = self.index.nearestNeighbor(point, 1)
            self.iface.mapCanvas().setMapTool(None)
            self.clickTool = PointTool(self.iface.mapCanvas())
            node_id = self.node_keys[nearest[0]]

            index_field = self.node_fields.index("node_id")
            node_actual_id = node_id[index_field]
            return node_actual_id
        except Exception as e:
            logger.error(e.args)

    def produces_path(self):
        self.to_but.setEnabled(True)
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
            QgsField("link_id", QVariant.LongLong),
            QgsField("a_node", QVariant.LongLong),
            QgsField("b_node", QVariant.LongLong),
            QgsField("direction", QVariant.Int),
        ]

        data = self.graph.graph.assign(__data_key__=self.graph.graph.link_id * self.graph.graph.direction)

        exclude = ["link_id", "a_node", "b_node", "direction", "__data_key__"]

        added_fields = [fld for fld in data if fld not in exclude]
        graph_fields.extend([QgsField(fld, QVariant.Double) for fld in added_fields])

        # add fields
        pr.addAttributes(graph_fields)
        vl.updateFields()  # tell the vector layer to fetch changes from the provider

        # add features
        all_links = []
        data = data[data["__data_key__"].isin(self.res.path * self.res.path_link_directions)]
        for _, rec in data.iterrows():
            fet = self.link_features[rec.link_id]
            attrs = [rec.link_id, rec.a_node, rec.b_node, int(rec.direction)]
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
