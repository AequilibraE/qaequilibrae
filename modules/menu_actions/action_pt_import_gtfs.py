from ..public_transport_procedures import GTFSImporter


def run_import_gtfs(qgisproject):
    if qgisproject.project is None:
        qgis_project.iface.messageBar().pushMessage("Error", "You need to load a project first", level=3, duration=10)
        return

    dlg2 = GTFSImporter(qgisproject)
    dlg2.show()
    dlg2.exec_()
