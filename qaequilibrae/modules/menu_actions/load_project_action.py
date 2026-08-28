from pathlib import Path


# Split loading between Qt action and processing, for easier unit testing
def run_load_project(qgis_project):
    if qgis_project.project:
        qgis_project.message_project_already_open()
        return

    from qaequilibrae.modules.common_tools.get_output_file_name import GetOutputFolderName

    proj_path = GetOutputFolderName(str(Path(qgis_project.path).parent), "AequilibraE Project folder")

    return _run_load_project_from_path(qgis_project, proj_path)


def _project_root(proj_path):
    """Maps a scenario folder back to the project root it belongs to"""
    path = Path(proj_path)
    if path.parent.name == "scenarios" and (path.parent.parent / "project_database.sqlite").is_file():
        return str(path.parent.parent)
    return proj_path


def _run_load_project_from_path(qgis_project, proj_path):
    from aequilibrae.project import Project

    if proj_path is None or proj_path == "":
        return

    proj_path = _project_root(proj_path)

    qgis_project.contents = []
    project = Project()

    try:
        project.open(proj_path)
    except FileNotFoundError as e:
        if e.args[0] == "Model does not exist. Check your path and try again":
            qgis_project.iface_error_message(
                "Check your path and try again", "FOLDER DOES NOT CONTAIN AN AEQUILIBRAE MODEL"
            )
            return
        else:
            raise e

    qgis_project.project = project
    show_project_in_panel(qgis_project, proj_path)


def show_project_in_panel(qgis_project, proj_path):
    """Fills the panel for a project AequilibraE already has open.

    Every way of getting to an open project - the menu, a QGIS project carrying a model, an
    import from OSM - has to come through here, or the plugin ends up holding a project whose
    scenarios and layers the panel knows nothing about.
    """
    from aequilibrae.project.tools import MigrationManager
    from aequilibrae.utils.spatialite_utils import connect_spatialite
    from qaequilibrae.modules.common_tools.get_output_file_name import remember_folder
    from qaequilibrae.modules.network.node_numbering import reserve_node_ids_for_centroids

    remember_folder(proj_path)

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

    # After the upgrade above, and after an OSM import has put AequilibraE's own triggers back
    reserve_node_ids_for_centroids(qgis_project.project)

    qgis_project.update_project_layers()

    qgis_project.message_log(f"Opened project on: {proj_path}")
