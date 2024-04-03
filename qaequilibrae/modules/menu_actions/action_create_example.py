def create_example(qgis_project):
    from qaequilibrae.modules.project_procedures import CreateExampleDialog

    dlg2 = CreateExampleDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
