from os.path import dirname, join

import numpy as np
from aequilibrae.paths.route_choice import RouteChoice

from qaequilibrae.modules.common_tools import Debouncer, BaseDialog
from qaequilibrae.modules.paths_procedures.plot_route_choice import plot_results


class ExecuteSingleDialog(BaseDialog):
    def __init__(self, qgis_project, graph, link_layer, parameters):
        super().__init__(
            ui_file=join(dirname(__file__), "forms/ui_execute_single.ui"),
            qgis_project=qgis_project,
            graph=graph,
            link_layer=link_layer,
            parameters=parameters,
        )

    def _base_ui_setup(self, **kwargs):
        self.graph = kwargs.get("graph")
        parameters = kwargs.get("parameters")
        self._algo = parameters["algorithm"]
        self._kwargs = parameters["kwargs"]
        self.demand = parameters["matrix"]
        self.link_layer = kwargs.get("link_layer")

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
