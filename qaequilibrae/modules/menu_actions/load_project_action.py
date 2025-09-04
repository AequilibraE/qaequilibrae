from os.path import join
from pathlib import Path
from tempfile import gettempdir


# Split loading between Qt action and processing, for easier unit testing
def run_load_project(qgis_project):
    if qgis_project.project:
        qgis_project.message_project_already_open()
        return

    from qaequilibrae.modules.common_tools.get_output_file_name import GetOutputFolderName

    proj_path = GetOutputFolderName(str(Path(qgis_project.path).parent), "AequilibraE Project folder")

    return _run_load_project_from_path(qgis_project, proj_path)


def _run_load_project_from_path(qgis_project, proj_path):
    from aequilibrae.project import Project

    if proj_path is None or proj_path == "":
        return

    if proj_path is not None and len(proj_path) > 0:
        qgis_project.contents = []
        qgis_project.project = Project()

        try:
            qgis_project.project.open(proj_path)
            qgis_project.message_log(f"Opened project on: {proj_path}")
        except FileNotFoundError as e:
            if e.args[0] == "Model does not exist. Check your path and try again":
                qgis_project.iface_error_message(
                    "Check your path and try again", "FOLDER DOES NOT CONTAIN AN AEQUILIBRAE MODEL"
                )
                return
            else:
                raise e

    pth = join(gettempdir(), "aequilibrae_last_folder.txt")
    with open(pth, "w") as file:
        file.write(proj_path)

    outdirs = qgis_project.project.list_scenarios()["scenario_name"].tolist()
    qgis_project.cob_scenarios.addItems(outdirs)
    qgis_project.available_scenarios.extend(outdirs)

    qgis_project.update_project_layers()
