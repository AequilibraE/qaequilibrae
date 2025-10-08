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

    # TODO: Select link analysis
    sl = dct.get("select_links")
    if sl:
        select_link = """\n\tfor tc in traffic_classes.values():\n\t\ttc.set_select_links({})"""
        func_string += select_link.format(sl)

    # Execute procedure
    func_string += "\n\tassig.execute()\n"

    # Save outputs
    func_string += f"\n\tassig.save_results('{dct.get("scenario_name")}')"

    if dct.get("skimming"):
        func_string += f"""\n\tassig.save_skims('{dct.get("scenario_name")}', which_ones="all", format="omx")"""

    # TODO: save select links outputs

    out_name = dct.get("out_name")
    project_path = dct.get("project_path")
    with open(out_name, "w") as file:
        file.write(func_string)

    with open(project_path / "run" / "__init__.py", "r") as file:
        lines = file.readlines()

    lines.insert(19, f"from .{out_name.split("/")[-1].split(".")[0]} import run_assignment\n")

    with open(project_path / "run" / "__init__.py", "w") as file:
        file.writelines(lines)
