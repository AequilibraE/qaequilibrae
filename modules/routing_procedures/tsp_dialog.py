import logging
import numpy as np
import os
from aequilibrae.paths import Graph, path_computation
from aequilibrae.paths.results import PathResults
from aequilibrae.project import Project

import qgis
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsVectorLayer, QgsField, QgsProject, QgsMarkerSymbol
from .tsp_procedure import TSPProcedure
from ..common_tools import ReportDialog

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/tsp.ui"))


class TSPDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, qgisproject):
        QtWidgets.QDialog.__init__(self)
        self.iface = qgisproject.iface
        self.setupUi(self)
        self.project = qgisproject.project  # type: Project
        self._PQgis = qgisproject

        self.link_layer = self._PQgis.layers["links"][0]
        self.node_layer = self._PQgis.layers["nodes"][0]

        QgsProject.instance().addMapLayer(self.link_layer)
        QgsProject.instance().addMapLayer(self.node_layer)

        self.all_modes = {}
        self.worker_thread: TSPProcedure = None
        self.but_run.clicked.connect(self.run)
        self.res = PathResults()

        self.rdo_selected.clicked.connect(self.populate_node_source)
        self.rdo_centroids.clicked.connect(self.populate_node_source)
        self.populate()
        self.populate_node_source()

    def populate_node_source(self):
        self.cob_start.clear()
        if self.rdo_selected.isChecked():
            centroids = self.selected_nodes()
        else:
            curr = self.project.network.conn.cursor()
            curr.execute("select node_id from nodes where is_centroid=1;")
            centroids = [i[0] for i in curr.fetchall()]
        for i in centroids:
            self.cob_start.addItem(str(i))

    def populate(self):
        curr = self.project.network.conn.cursor()
        curr.execute("""select mode_name, mode_id from modes""")
        for x in curr.fetchall():
            self.cob_mode.addItem(f"{x[0]} ({x[1]})")
            self.all_modes[f"{x[0]} ({x[1]})"] = x[1]

        for f in self.project.network.skimmable_fields():
            self.cob_minimize.addItem(f)

    def selected_nodes(self) -> list:
        idx = self.node_layer.dataProvider().fieldNameIndex("node_id")
        c = [int(feat.attributes()[idx]) for feat in self.node_layer.selectedFeatures()]
        return sorted(c)

    def run(self):
        md = self.all_modes[self.cob_mode.currentText()]

        self.project.network.build_graphs(modes=[md])
        self.graph = self.project.network.graphs[md]

        if self.rdo_selected.isChecked():
            centroids = self.selected_nodes()
            if len(centroids) < 3:
                qgis.utils.iface.messageBar().pushMessage("You need at least three nodes to route. ", "", level=3)
                return
            centroids = np.array(centroids).astype(np.int64)
            self.graph.prepare_graph(centroids=centroids)
        else:
            if self.project.network.count_centroids() < 3:
                qgis.utils.iface.messageBar().pushMessage("You need at least three centroids to route. ", "", level=3)
                return

        self.graph.set_graph(self.cob_minimize.currentText())  # let's say we want to minimize time
        self.graph.set_blocked_centroid_flows(self.chb_block.isChecked())
        self.graph.set_skimming([self.cob_minimize.currentText()])  # And will skim time and distance
        depot = int(self.cob_start.currentText())
        vehicles = 1
        self.res.prepare(self.graph)
        self.worker_thread = TSPProcedure(qgis.utils.iface.mainWindow(), self.graph, depot, vehicles)
        self.run_thread()

    def run_thread(self):
        self.worker_thread.finished.connect(self.finished)
        self.worker_thread.start()
        self.exec_()

    def finished(self):
        ns = self.worker_thread.node_sequence
        print(ns)
        if len(ns) < 2:
            return

        all_links = []
        for i in range(1, len(ns)):
            self.res.reset()
            path_computation(ns[i - 1], ns[i], self.graph, self.res)
            all_links.extend(list(self.res.path))

        if self.rdo_new_layer.isChecked():
            self.create_path_with_scratch_layer(all_links)
        else:
            self.create_path_with_selection(all_links)
        self.close()

        if self.worker_thread.report is not None:
            dlg2 = ReportDialog(self.iface, self.worker_thread.report)
            dlg2.show()
            dlg2.exec_()

    def create_path_with_selection(self, all_links):
        f = "link_id"
        t = " or ".join([f"{f}={k}" for k in all_links])
        self.link_layer.selectByExpression(t)

    def create_path_with_scratch_layer(self, path_links):
        # Create TSP route
        crs = self.link_layer.dataProvider().crs().authid()
        vl = QgsVectorLayer(f"LineString?crs={crs}", "TSP Solution", "memory")
        pr = vl.dataProvider()

        # add fields
        pr.addAttributes(self.link_layer.dataProvider().fields())
        vl.updateFields()  # tell the vector layer to fetch changes from the provider

        idx = self.link_layer.dataProvider().fieldNameIndex("link_id")
        self.link_features = {}
        for feat in self.link_layer.getFeatures():
            link_id = feat.attributes()[idx]
            self.link_features[link_id] = feat

        # add a feature
        all_links = []
        for k in path_links:
            fet = self.link_features[k]
            all_links.append(fet)

        # add all links to the temp layer
        pr.addFeatures(all_links)

        # add layer to the map
        QgsProject.instance().addMapLayer(vl)

        symbol = vl.renderer().symbol()
        symbol.setWidth(1.6)
        qgis.utils.iface.mapCanvas().refresh()

        # Create TSP stops
        crs = self.node_layer.dataProvider().crs().authid()
        nl = QgsVectorLayer(f"Point?crs={crs}", "TSP Stops", "memory")
        pn = nl.dataProvider()

        # add fields
        pn.addAttributes(self.node_layer.dataProvider().fields())
        nl.updateFields()  # tell the vector layer to fetch changes from the provider

        idx = self.node_layer.dataProvider().fieldNameIndex("node_id")
        self.node_features = {}
        for feat in self.node_layer.getFeatures():
            node_id = feat.attributes()[idx]
            self.node_features[node_id] = feat

        # add the feature
        stop_nodes = []
        seq = {}
        for i, k in enumerate(self.worker_thread.node_sequence[:-1]):
            fet = self.node_features[k]
            stop_nodes.append(fet)
            seq[k] = i + 1

        # add all links to the temp layer
        pn.addFeatures(stop_nodes)

        # Goes back and adds the order of visitation for each node
        pn.addAttributes([QgsField("sequence", QVariant.Int)])
        nl.updateFields()
        sdx = nl.dataProvider().fieldNameIndex("sequence")

        nl.startEditing()
        for feat in nl.getFeatures():
            node_id = feat.attributes()[idx]
            nl.changeAttributeValue(feat.id(), sdx, seq[node_id])

        nl.commitChanges()

        # add layer to the map
        QgsProject.instance().addMapLayer(nl)
        symbol = QgsMarkerSymbol.createSimple({"name": "star", "color": "red"})
        symbol.setSize(6)
        nl.renderer().setSymbol(symbol)

        qgis.utils.iface.mapCanvas().refresh()
