import os
from qgis.core import QgsVectorLayer
from qgis.core import QgsProject
from qgis.PyQt.QtCore import QObject
from qgis.PyQt import QtWidgets, uic
import qgis
import numpy as np
from .tsp_procedure import TSPProcedure

from ..common_tools.global_parameters import *

no_binary = False
try:
    from aequilibrae.paths import Graph, path_computation
    from aequilibrae.paths.results import PathResults
    from aequilibrae.project import Project
except:
    no_binary = True

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/tsp.ui"))


class TSPDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, project: Project, link_layer, node_layer):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.project = project
        self.link_layer = link_layer
        self.node_layer = node_layer
        self.all_modes = {}
        self.worker_thread: TSPProcedure = None
        self.but_run.clicked.connect(self.run)
        self.res = PathResults()

        self.populate()

    def populate(self):
        curr = self.project.network.conn.cursor()
        curr.execute("""select mode_name, mode_id from modes""")
        for x in curr.fetchall():
            self.cob_mode.addItem(f'{x[0]} ({x[1]})')
            self.all_modes[f'{x[0]} ({x[1]})'] = x[1]

        for f in self.project.network.skimmable_fields():
            self.cob_minimize.addItem(f)

        curr = self.project.network.conn.cursor()
        curr.execute('select node_id from nodes where is_centroid=1;')
        for i in curr.fetchall():
            self.cob_start.addItem(str(i[0]))

    def run(self):
        error = None
        md = self.all_modes[self.cob_mode.currentText()]

        self.project.network.build_graphs()
        self.graph = self.project.network.graphs[md]

        if self.rdo_selected.isChecked():
            centroids = []
            self.graph.prepare_graph(centroids=centroids)

        self.graph.set_graph(self.cob_minimize.currentText())  # let's say we want to minimize time
        self.graph.set_blocked_centroid_flows(self.chb_block.isChecked())
        self.graph.set_skimming([self.cob_minimize.currentText()])  # And will skim time and distance
        depot = int(self.cob_start.currentText())
        vehicles = 1
        self.res.prepare(self.graph)
        self.worker_thread = TSPProcedure(qgis.utils.iface.mainWindow(), self.graph, depot, vehicles)
        self.run_thread()
        # qgis.utils.iface.messageBar().pushMessage("Input data not provided correctly. ", error, level=3)

    def run_thread(self):
        self.worker_thread.ProgressValue.connect(self.progress_value_from_thread)
        self.worker_thread.ProgressMaxValue.connect(self.progress_range_from_thread)
        self.worker_thread.ProgressText.connect(self.progress_text_from_thread)

        self.worker_thread.finished_threaded_procedure.connect(self.finished)
        self.worker_thread.start()
        self.exec_()

    def progress_range_from_thread(self, value):
        self.progressbar.setRange(0, value)

    def progress_text_from_thread(self, value):
        self.progress_label.setText(value)

    def progress_value_from_thread(self, value):
        self.progressbar.setValue(value)

    def finished(self, procedure):
        ns = self.worker_thread.node_sequence

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

    def create_path_with_selection(self, all_links):
        f = 'link_id'
        t = " or ".join([f"{f}={k}" for k in all_links])
        self.link_layer.selectByExpression(t)

    def create_path_with_scratch_layer(self, path_links):
        crs = self.link_layer.dataProvider().crs().authid()
        vl = QgsVectorLayer(f"LineString?crs={crs}", 'TSP Solution', "memory")
        pr = vl.dataProvider()

        # add fields
        pr.addAttributes(self.link_layer.dataProvider().fields())
        vl.updateFields()  # tell the vector layer to fetch changes from the provider

        idx = self.link_layer.dataProvider().fieldNameIndex('link_id')
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
        symbol.setWidth(1)
        qgis.utils.iface.mapCanvas().refresh()