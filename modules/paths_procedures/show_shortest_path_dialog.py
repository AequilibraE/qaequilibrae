import logging
import os
import sys
from aequilibrae.paths import path_computation
from aequilibrae.paths.results import PathResults
from aequilibrae.project import Project
from qgis._core import QgsProject, QgsVectorLayer, QgsSpatialIndex

import qgis
from qgis.PyQt import QtCore
from qgis.PyQt import QtWidgets, uic
from qgis.utils import iface
from .point_tool import PointTool
from ..common_tools import LoadGraphLayerSettingDialog
from ..common_tools import standard_path

logger = logging.getLogger("AequilibraEGUI")

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/aequilibrae/")

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_compute_path.ui"))


class ShortestPathDialog(QtWidgets.QDialog, FORM_CLASS):
    clickTool = PointTool(iface.mapCanvas())

    def __init__(self, qgis_project) -> None:
        # QtWidgets.QDialog.__init__(self)
        QtWidgets.QDialog.__init__(self)
        self.iface = qgis_project.iface
        self.project = qgis_project.project  # type: Project
        self.setupUi(self)
        self.field_types = {}
        self.centroids = None
        self.node_layer = qgis_project.layers["nodes"][0]
        self.line_layer = qgis_project.layers["links"][0]
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
        self.do_dist_matrix.setText("Loading data")
        self.from_but.setEnabled(False)
        self.to_but.setEnabled(False)
        dlg2 = LoadGraphLayerSettingDialog(self.iface, self.project)
        dlg2.show()
        dlg2.exec_()
        if len(dlg2.error) < 1 and len(dlg2.mode) > 0:
            self.mode = dlg2.mode
            self.minimize_field = dlg2.minimize_field

            if self.mode not in self.project.network.graphs:
                self.project.network.build_graphs(modes=[self.mode])

            if dlg2.remove_chosen_links:
                self.graph = self.project.network.graphs.pop(self.mode)
            else:
                self.graph = self.project.network.graphs[self.mode]
            self.graph.set_graph(self.minimize_field)
            self.graph.set_skimming([self.minimize_field])
            self.graph.set_blocked_centroid_flows(dlg2.block_connector)

            if dlg2.remove_chosen_links:
                idx = self.line_layer.dataProvider().fieldNameIndex("link_id")
                remove = [feat.attributes()[idx] for feat in self.line_layer.selectedFeatures()]
                self.graph.exclude_links(remove)

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

            self.do_dist_matrix.setText("Display")
            self.do_dist_matrix.setEnabled(True)
            self.from_but.setEnabled(True)
            self.to_but.setEnabled(True)

    def clear_memory_layer(self):
        self.link_features = None

    def search_for_point_from(self):
        self.clickTool.clicked.connect(self.fill_path_from)
        self.iface.mapCanvas().setMapTool(self.clickTool)
        self.from_but.setEnabled(False)

    def search_for_point_to(self):
        self.iface.mapCanvas().setMapTool(self.clickTool)
        self.clickTool.clicked.connect(self.fill_path_to)
        self.to_but.setEnabled(False)

    def search_for_point_to_after_from(self):
        self.iface.mapCanvas().setMapTool(self.clickTool)
        self.clickTool.clicked.connect(self.fill_path_to)

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
                msg = f"No path between {self.path_from.text()} and {self.path_to.text()}"
                qgis.utils.iface.messageBar().pushMessage(msg, "", level=3)

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

        # add fields
        pr.addAttributes(self.line_layer.dataProvider().fields())
        vl.updateFields()  # tell the vector layer to fetch changes from the provider

        # add a feature
        all_links = []
        for k in self.res.path:
            fet = self.link_features[k]
            all_links.append(fet)

        # add all links to the temp layer
        pr.addFeatures(all_links)

        # add layer to the map
        QgsProject.instance().addMapLayer(vl)

        symbol = vl.renderer().symbol()
        symbol.setWidth(1)
        qgis.utils.iface.mapCanvas().refresh()

    def exit_procedure(self):
        self.close()
