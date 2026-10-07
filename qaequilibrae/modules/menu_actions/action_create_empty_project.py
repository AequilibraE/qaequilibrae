"""Create an empty project from the menu, then open it in the plugin panel."""


def create_empty_project(qgis_project):
    from processing import execAlgorithmDialog

    from .load_project_action import _run_load_project_from_path

    if qgis_project.project is not None:
        qgis_project.message_project_already_open()
        return
    result = execAlgorithmDialog("qaequilibrae:create_empty_project")
    if result and result.get("Output"):
        _run_load_project_from_path(qgis_project, result["Output"])
