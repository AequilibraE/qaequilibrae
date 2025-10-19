from pathlib import Path


def create_strings(dct: dict):
    # Set up file main strings
    func_string = """from aequilibrae.context import get_active_project
\ndef run_assignment():
\tfrom aequilibrae.paths import TrafficAssignment, TrafficClass
\tproject = get_active_project()
\tproject.network.build_graphs()
\tmatrices = project.matrices
\n\ttraffic_classes = []\n
"""

    # Set up traffic class strings
    loop = """\tgraph = project.network.graphs['{}']
\tgraph.set_graph('{}')
\tgraph.set_skimming({})
\tgraph.set_blocked_centroid_flows({})
\n\tdemand = matrices.get_matrix('{}')
\tdemand.computational_view(['{}'])
\n\ttraffic_classes.extend([TrafficClass(name='{}', graph=graph, matrix=demand)])
"""
    for params in dct["classes"]:
        func_string += loop.format(*params)

    # Set up traffic assignment strings
    assignment = """\n\tassig = TrafficAssignment()
\tassig.set_classes(traffic_classes)
\tassig.set_vdf('{}')
\tassig.set_vdf_parameters({})
\tassig.set_capacity_field('{}')
\tassig.set_time_field('{}')
\tassig.set_algorithm('{}')
\tassig.max_iter = {}
\tassig.rgap_target = {}
"""
    func_string += assignment.format(*dct.get("assignment"))

    sl = dct.get("select_links")
    if sl:
        select_link = """\n\tfor tc in traffic_classes.values():\n\t\ttc.set_select_links({})"""
        func_string += select_link.format(sl["select_links"])

    # Execute procedure
    func_string += "\n\tassig.execute()\n"

    # Save outputs
    func_string += "\n\tassig.save_results('{}')".format(dct.get("scenario_name"))

    if dct.get("skimming"):
        func_string += "\n\tassig.save_skims('{}', which_ones='all', format='omx')".format(dct.get("scenario_name"))

    if sl:
        if sl["save_matrix"]:
            func_string += "\n\tassig.save_select_link_matrices('{}')".format(sl["output_name"])
        if sl["save_result"]:
            func_string += "\n\tassig.save_select_link_flows('{}')".format(sl["output_name"])

    out_name = dct.get("out_name")
    project_path = dct.get("project_path")
    with open(out_name, "w") as file:
        file.write(func_string)

    with open(project_path / "run" / "__init__.py", "r") as file:
        lines = file.readlines()

    # Find the last import statement to insert after
    pth_string = "from .{} import run_assignment\n".format(Path(out_name).stem)
    lines.insert(0, pth_string)

    with open(project_path / "run" / "__init__.py", "w") as file:
        file.writelines(lines)
