def run_import_gtfs(qgis_project):
    from qaequilibrae.modules.public_transport_procedures import GTFSImporter

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    dlg2 = GTFSImporter(qgis_project)
    dlg2.show()
    dlg2.exec_()
