def display_aequilibrae_formats(qgis_project):
    from qaequilibrae.modules.matrix_procedures import DisplayAequilibraEFormatsDialog
    dlg2 = DisplayAequilibraEFormatsDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
