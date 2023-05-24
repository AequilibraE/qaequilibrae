def load_matrices(qgis_project):
    from ..matrix_procedures import LoadMatrixDialog
    dlg2 = LoadMatrixDialog(qgis_project.iface, sparse=True, multiple=True, single_use=False)
    dlg2.show()
    dlg2.exec_()
