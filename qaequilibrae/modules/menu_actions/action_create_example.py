def create_example(qgis_project):
    from qaequilibrae.modules.project_procedures import CreateExampleDialog

    if qgis_project.project is not None:
        qgis_project.message_project_already_open()
        return
    dlg2 = CreateExampleDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
