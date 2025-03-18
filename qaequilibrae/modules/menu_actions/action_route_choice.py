def run_route_choice(qgis_project):
    from qaequilibrae.modules.paths_procedures.route_choice_dialog import RouteChoiceDialog

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    dlg2 = RouteChoiceDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
