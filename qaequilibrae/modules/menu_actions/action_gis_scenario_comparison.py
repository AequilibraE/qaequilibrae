def run_scenario_comparison(qgis_project):
    from qaequilibrae.modules.gis import CompareScenariosDialog

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    dlg2 = CompareScenariosDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
