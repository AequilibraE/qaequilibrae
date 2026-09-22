from pathlib import Path
from pprint import pformat


def create_strings(dct: dict):
    """Write a small project-runner that delegates to the Processing operation."""
    configuration = _configuration(dct)
    source = f"""from aequilibrae.context import get_active_project

from qaequilibrae.modules.processing_provider.paths_procedures.traffic_assignment import run_traffic_assignment


def run_assignment():
    return run_traffic_assignment(get_active_project(), {pformat(configuration, sort_dicts=False)})
"""

    out_name = Path(dct["out_name"])
    out_name.write_text(source, encoding="utf-8")

    init_path = Path(dct["project_path"]) / "run" / "__init__.py"
    lines = init_path.read_text(encoding="utf-8").splitlines(keepends=True)
    lines.insert(0, f"from .{out_name.stem} import run_assignment\n")
    init_path.write_text("".join(lines), encoding="utf-8")


def _configuration(dct):
    vdf, vdf_parameters, capacity, time_field, algorithm, max_iter, rgap = dct["assignment"]
    traffic_classes = []
    for traffic_class in dct["classes"]:
        mode, _, skims, blocked_centroid_flows, matrix_name, matrix_cores, name, pce = traffic_class
        traffic_classes.append(
            {
                name: {
                    "matrix_name": matrix_name,
                    "matrix_cores": matrix_cores,
                    "network_mode": mode,
                    "pce": pce,
                    "blocked_centroid_flows": blocked_centroid_flows,
                    "skims": {skim: ["final", "blended"] for skim in skims},
                }
            }
        )

    configuration = {
        "traffic_classes": traffic_classes,
        "assignment": {
            "algorithm": algorithm,
            "max_iter": max_iter,
            "rgap": rgap,
            "vdf": vdf,
            **vdf_parameters,
            "capacity_field": capacity,
            "time_field": time_field,
            "result_name": dct["scenario_name"],
        },
    }
    if select_links := dct.get("select_links"):
        configuration["select_links"] = {
            "selection": select_links["select_links"][0],
            "output_name": select_links["output_name"],
            "save_matrix": select_links["save_matrix"],
            "save_result": select_links["save_result"],
        }
    return configuration
