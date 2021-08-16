from ..project_procedures import AddZonesDialog


def run_add_zones(qgis_project):
    if qgis_project.project is None:
        self.iface.messageBar().pushMessage("Error", "You need to load a project first", level=3, duration=10)
        return
    dlg2 = AddZonesDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
