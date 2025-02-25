import os

import numpy as np
from aequilibrae.paths.route_choice import RouteChoice
from qgis.PyQt import uic
from qgis.PyQt.QtCore import pyqtSlot
from qgis.PyQt.QtWidgets import QDialog

from qaequilibrae.modules.common_tools.debouncer import Debouncer
from qaequilibrae.modules.paths_procedures.plot_route_choice import plot_results

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_execute_single.ui"))


class VisualizeSingle(QDialog, FORM_CLASS):
    def __init__(self, iface, graph, algorithm, kwargs, from_node, to_node, demand, link_layer):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.graph = graph
        self._algo = algorithm
        self._kwargs = kwargs
        self.demand = demand
        self.link_layer = link_layer

        self.node_from.setText(str(from_node))
        self.node_to.setText(str(to_node))
        self.sld_max_routes.setValue(self._kwargs["max_routes"])
        self.label_4.setText(f"Number of routes: {self._kwargs["max_routes"]}")

        self.debouncer = Debouncer(delay_ms=1_000, callback=self.on_input_changed)

        self.node_from.returnPressed.connect(self._on_node_changed)
        self.node_to.returnPressed.connect(self._on_node_changed)
        self.sld_max_routes.valueChanged.connect(self._on_slider_changed)

    def execute_single(self):
        from_node = int(self.node_from.text())
        to_node = int(self.node_to.text())
        self._kwargs["max_routes"] = self.sld_max_routes.value()

        nodes_of_interest = np.array([from_node, to_node], dtype=np.int64)

        self.graph.prepare_graph(nodes_of_interest)
        self.graph.set_graph("utility")

        rc = RouteChoice(self.graph)
        rc.set_choice_set_generation(self._algo, **self._kwargs)
        _ = rc.execute_single(from_node, to_node, self.demand)

        plot_results(rc.get_results().to_pandas(), from_node, to_node, self.link_layer)

    def exit_procedure(self):
        self.close()

    @pyqtSlot()
    def _on_node_changed(self):
        self.debouncer(("node_changed"))

    @pyqtSlot()
    def _on_slider_changed(self):
        self.label_4.setText(f"Number of routes: {self._kwargs["max_routes"]}")
        self.debouncer(("slider_changed"))

    def on_input_changed(self):
        self.execute_single()
