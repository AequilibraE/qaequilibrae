

def run_show_project_data(qgis_project):
    from ..matrix_procedures import LoadProjectDataDialog
    if qgis_project.project is None:
        qgis_project.iface.messageBar().pushMessage("Error", "You need to load a project first", level=3, duration=10)
        return
    dlg2 = LoadProjectDataDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
