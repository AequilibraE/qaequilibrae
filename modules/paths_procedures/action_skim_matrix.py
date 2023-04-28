

def run_dist_matrix(qgis_project):
    from .impedance_matrix_dialog import ImpedanceMatrixDialog
    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return
    dlg2 = ImpedanceMatrixDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
