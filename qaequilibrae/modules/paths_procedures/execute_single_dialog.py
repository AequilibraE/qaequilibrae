import os

import numpy as np
from aequilibrae.paths.route_choice import RouteChoice
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

from qaequilibrae.modules.common_tools.debouncer import Debouncer
from qaequilibrae.modules.paths_procedures.plot_route_choice import plot_results

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_execute_single.ui"))


class ExecuteSingleDialog(QDialog, FORM_CLASS):
    def __init__(self, iface, graph, link_layer, parameters):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)

        self.graph = graph
        self._algo = parameters["algorithm"]
        self._kwargs = parameters["kwargs"]
        self.demand = parameters["matrix"]
        self.link_layer = link_layer

        self.node_from.setText(str(parameters["node_from"]))
        self.node_to.setText(str(parameters["node_to"]))
        self.sld_max_routes.setValue(self._kwargs["max_routes"])
        self.label_4.setText(f"Number of routes: {self._kwargs["max_routes"]}")

        self.debouncer = Debouncer(delay_ms=700, callback=self.execute_single)

        self.node_from.editingFinished.connect(self.execute_single)
        self.node_from.textChanged.connect(self._on_node_from_changed)
        self.node_to.editingFinished.connect(self.execute_single)
        self.node_to.textChanged.connect(self._on_node_to_changed)
        self.sld_max_routes.valueChanged.connect(self._on_slider_changed)
        self.sld_max_routes.sliderReleased.connect(self.execute_single)

    def execute_single(self):
        from_node = int(self.node_from.text())
        to_node = int(self.node_to.text())

        nodes_of_interest = np.array([from_node, to_node], dtype=np.int64)

        self.graph.prepare_graph(nodes_of_interest)
        self.graph.set_graph("utility")

        rc = RouteChoice(self.graph)
        rc.set_choice_set_generation(self._algo, **self._kwargs)
        _ = rc.execute_single(from_node, to_node, self.demand)

        plot_results(rc.get_results(), from_node, to_node, self.link_layer)

    def exit_procedure(self):
        self.close()

    def _on_node_from_changed(self):
        self.debouncer()

    def _on_node_to_changed(self):
        self.debouncer()

    def _on_slider_changed(self, value):
        self.label_4.setText(f"Number of routes: {value}")
        self._kwargs["max_routes"] = value
