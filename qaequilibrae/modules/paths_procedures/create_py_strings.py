def create_strings(dct: dict):
    # Set up file main strings
    func_string = """from aequilibrae.context import get_active_project\n
def run_assignment():
\tfrom aequilibrae.paths import TrafficAssignment, TrafficClass
\n
\tproject = get_active_project()\n
"""

    # Set up traffic class strings
    classes = """

"""
    func_string += classes

    # Set up traffic assignment strings
    assignment = """
\tassig = TrafficAssignment()
\tassig.set_classes(assigclass)
\tassig.set_vdf('{}')
\tassig.set_vdf_parameters({})
\tassig.set_capacity_field('{}')
\tassig.set_time_field('{}')
\tassig.set_algorithm('{}')
\tassig.max_iter = {}
\tassig.rgap_target = {}
"""
    func_string += assignment.format(*dct.get("assignment"))

    # Select link analysis
    # sl = dct.get("select_links")
    # if sl:
    #     select_link = """\trc.set_select_links({})"""
    #     func_string += select_link.format(sl)

    # Execute procedure
    func_string += "\n\tassig.execute()\n"

    # Save outputs
    func_string += f"\n\tassig.save_results({dct.get("scenario_name")})"

    if dct.get("skimming"):
        func_string += f"""\n\tassig.save_skims({dct.get("scenario_name")}, which_ones="all", format="omx")"""

    return func_string
