def run_show_project_data(qgis_project):
    from qaequilibrae.modules.matrix_procedures import LoadProjectDataDialog

    has_project = False if qgis_project.project is None else True

    dlg2 = LoadProjectDataDialog(qgis_project, has_project)
    dlg2.show()
    dlg2.exec_()
