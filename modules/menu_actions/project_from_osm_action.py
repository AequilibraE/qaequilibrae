def project_from_osm(qgis_project):
    from ..project_procedures import ProjectFromOSMDialog
    if qgis_project.project is not None:
        qgis_project.message_project_already_open()
        return
    dlg2 = ProjectFromOSMDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
