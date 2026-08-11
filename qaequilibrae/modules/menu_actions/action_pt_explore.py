def run_pt_explore(qgis_project):
    from qaequilibrae.modules.transit_procedures import TransitNavigatorDialog
    from qaequilibrae.modules.common_tools.auxiliary_functions import project_has_transit

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    elif not project_has_transit(qgis_project.project):
        qgis_project.message_no_gtfs_feed()
        return

    dlg2 = TransitNavigatorDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
