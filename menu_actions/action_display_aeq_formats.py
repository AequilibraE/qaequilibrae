from ..matrix_procedures import DisplayAequilibraEFormatsDialog


def display_aequilibrae_formats(qgis_project):
    dlg2 = DisplayAequilibraEFormatsDialog(qgis_project.iface)
    dlg2.show()
    dlg2.exec_()
