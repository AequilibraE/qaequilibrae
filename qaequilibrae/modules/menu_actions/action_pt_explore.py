def run_pt_explore(qgis_project):
    from qaequilibrae.modules.public_transport_procedures.transit_navigator_dialog import TransitNavigatorDialog
    from os.path import exists, join

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    elif not exists(join(qgis_project.project.project_base_path, "public_transport.sqlite")):
        qgis_project.message_no_gtfs_feed()
        return

    dlg2 = TransitNavigatorDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
