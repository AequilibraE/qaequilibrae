"""Shared execution for the transit assignment dialog and Processing algorithm."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.paths import TransitAssignment, TransitClass
from aequilibrae.transit import Transit
from aequilibrae.transit.transit_graph_builder import TransitGraphBuilder

Progress = Callable[[int, int, str], None]
Cancelled = Callable[[], bool]


def run_transit_assignment(
    project: Any,
    transit_data: Any,
    configs: dict[str, Any],
    action: str,
    *,
    progress: Progress | None = None,
    is_canceled: Cancelled | None = None,
) -> dict[str, Any]:
    """Run transit skimming or assignment with shared dialog/toolbox behavior."""

    def report(step: int, message: str) -> None:
        if progress:
            progress(step, 10, message)
        check_canceled()

    def check_canceled() -> None:
        if is_canceled and is_canceled():
            raise InterruptedError("Transit assignment was canceled")

    if action not in {"create", "assign"}:
        raise ValueError(f"Unknown transit operation: {action}")

    transit_data = transit_data or Transit(project)
    if action == "create":
        matrix_name = configs["matrix_name"]
        if not isinstance(matrix_name, str) or not matrix_name.strip():
            raise ValueError("A skim matrix name is required")
        if Path(matrix_name).name != matrix_name or "\\" in matrix_name:
            raise ValueError("Matrix names must not contain directory separators")
        matrix_path = Path(project.project_base_path) / "matrices" / f"{matrix_name}.omx"
        if project.matrices.check_exists(matrix_name) or matrix_path.exists():
            raise ValueError(f"Matrix '{matrix_name}' already exists")

    report(1, "Creating transit graph")
    if configs["has_graph"]:
        graph_builder = TransitGraphBuilder.from_db(project, configs["period_id"])
    else:
        graph_builder = transit_data.create_graph(
            period_id=configs["period_id"],
            with_outer_stop_transfers=configs["with_outer_stop_transfers"],
            with_inner_stop_transfers=configs["with_inner_stop_transfers"],
            with_walking_edges=configs["with_walking_edges"],
            blocking_centroid_flows=configs["blocking_centroid_flows"],
            connector_method=configs["connector_method"],
        )
        report(2, "Building network graphs")
        project.network.build_graphs()
        report(3, "Creating line geometry")
        graph_builder.create_line_geometry(method=configs["line_method"], graph=configs["mode_id"])
        if configs["save_graph"]:
            report(4, "Saving transit graph")
            transit_data.save_graphs(period_ids=[configs["period_id"]])

    report(5, "Converting transit graph")
    graph = graph_builder.to_transit_graph()
    matrix = None
    try:
        if action == "create":
            report(6, "Creating skim demand matrix")
            centroids = graph.centroids
            if centroids is None:
                raise ValueError("Transit graph has no centroids")
            zone_count = len(centroids)
            matrix = AequilibraeMatrix()
            matrix.create_empty(zones=zone_count, matrix_names=["pt"], memory_only=True)
            if matrix.index is None or matrix.matrices is None:
                raise RuntimeError("Could not allocate the transit skim matrix")
            matrix.index[:] = graph.centroids[:]
            matrix.matrices[:, :, 0] = np.ones((zone_count, zone_count))
            matrix.computational_view()
        else:
            report(6, "Loading demand matrix")
            matrix = project.matrices.get_matrix(configs["mat_name"])
            if matrix.index is None or graph.centroids is None:
                raise ValueError("Demand matrix or transit graph has no zone index")
            matrix.computational_view(configs["mat_core"])
            matrix_zones = np.asarray(matrix.index[:])
            graph_zones = np.asarray(graph.centroids)
            if len(matrix_zones) != len(graph_zones):
                raise ValueError("Demand matrix and transit graph have different zone sets")
            matrix_positions = {int(zone): position for position, zone in enumerate(matrix_zones)}
            if len(matrix_positions) != len(matrix_zones) or set(matrix_positions) != {
                int(zone) for zone in graph_zones
            }:
                raise ValueError("Demand matrix and transit graph have different zone sets")
            if not np.array_equal(matrix_zones, graph_zones):
                order = np.fromiter((matrix_positions[int(zone)] for zone in graph_zones), dtype=np.intp)
                reordered_matrix = AequilibraeMatrix()
                try:
                    cores = list(configs["mat_core"])
                    reordered_matrix.create_empty(zones=len(graph_zones), matrix_names=cores, memory_only=True)
                    if reordered_matrix.index is None:
                        raise RuntimeError("Could not allocate the reordered demand matrix index")
                    reordered_matrix.index[:] = graph_zones
                    for core in cores:
                        reordered_matrix.matrix[core][:, :] = matrix.get_matrix(core)[np.ix_(order, order)]
                    reordered_matrix.computational_view(cores)
                except Exception:
                    reordered_matrix.close()
                    raise
                matrix.close()
                matrix = reordered_matrix

        report(7, "Creating transit class")
        transit_class = TransitClass(name=configs["class_name"], graph=graph, matrix=matrix)
        assignment = TransitAssignment()
        assignment.add_class(transit_class)
        assignment.set_time_field(configs["time_field"])
        assignment.set_frequency_field(configs["frequency_field"])
        assignment.set_algorithm("os")
        if action == "create":
            assignment.set_skimming_fields(configs["skim_fields"])
        transit_class.set_demand_matrix_core(configs["demand_matrix_core"])

        report(8, "Preparing transit assignment")
        check_canceled()
        report(9, "Running transit assignment")
        assignment.execute()
        check_canceled()

        report(10, "Saving transit results")
        if action == "create":
            output_path = Path(project.project_base_path) / "matrices" / f"{configs['matrix_name']}.omx"
            skim_results = assignment.get_skim_results()
            skim_result = skim_results[configs["class_name"]] if isinstance(skim_results, dict) else skim_results[0]
            skim_result.export(str(output_path))
            project.matrices.update_database()
            project.matrices.reload()
            return {"matrix": str(output_path)}

        assignment.save_results(table_name=configs["result_name"])
        return {"result_name": configs["result_name"]}
    finally:
        if matrix is not None:
            matrix.close()
