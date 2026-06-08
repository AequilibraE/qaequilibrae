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
    from aequilibrae.project.tools import MigrationManager
    from aequilibrae.utils.spatialite_utils import connect_spatialite

    if proj_path is None or proj_path == "":
        return

    if proj_path is not None and len(proj_path) > 0:
        qgis_project.contents = []
        qgis_project.project = Project()

        try:
            qgis_project.project.open(proj_path)
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

    try:
        outdirs = qgis_project.project.list_scenarios()["scenario_name"].tolist()
    except Exception as e:
        qgis_project.message_log(f"Exception: {str(e)}.")
        qgis_project.message_log("Upgrading project database to handle exception")
        # This is a copy of AequilibraE's `project.upgrade()` to upgrade only project_database.
        connections = {
            "project_conn": connect_spatialite(qgis_project.project._project_database_path),
            "transit_conn": None,
            "results_conn": None,
        }
        mm = MigrationManager(MigrationManager.network_migration_file)
        with connections["project_conn"] as conn:
            mm.mark_all_as_seen(conn)
        mm.upgrade("project_conn", connections=connections)
        qgis_project.message_log("Completed database upgrades")
        connections["project_conn"].close()
        outdirs = qgis_project.project.list_scenarios()["scenario_name"].tolist()

    qgis_project.cob_scenarios.addItems(outdirs)
    qgis_project.available_scenarios.extend(outdirs)

    qgis_project.update_project_layers()

    qgis_project.message_log(f"Opened project on: {proj_path}")
