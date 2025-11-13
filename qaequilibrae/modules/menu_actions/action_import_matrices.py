def load_matrices(qgis_project):
    from qaequilibrae.modules.matrix_procedures import LoadMatrixDialog

    dlg2 = LoadMatrixDialog(qgis_project, sparse=True, multiple=True)
    dlg2.show()
    dlg2.exec_()
