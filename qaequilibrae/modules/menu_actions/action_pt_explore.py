def run_pt_explore(qgis_project):
    from qaequilibrae.modules.public_transport_procedures.transit_navigator_dialog import TransitNavigatorDialog
    from os.path import exists, join

    if qgis_project.project is None:
        qgis_project.iface.messageBar().pushMessage("Error", "You need to load a project first", level=3, duration=10)
        return

    elif not exists(join(qgis_project.project.project_base_path, "public_transport.sqlite")):
        qgis_project.iface.messageBar().pushMessage(
            "Error", "You need to import a GTFS feed first", level=3, duration=10
        )
        return

    dlg2 = TransitNavigatorDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
