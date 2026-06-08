def create_scenarios(qgis_project):
    from qaequilibrae.modules.project_procedures import CreateScenariosDialog

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    dlg2 = CreateScenariosDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
