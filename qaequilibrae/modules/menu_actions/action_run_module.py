def run_module(qgis_project):
    from qaequilibrae.modules.project_procedures import RunModuleDialog
    from aequilibrae import Parameters

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    if qgis_project.project:
        p = Parameters()
        if "run" not in p.parameters:
            qgis_project.iface_warning_message("'Run procedures' is not available for this project.")
            return

    dlg2 = RunModuleDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
