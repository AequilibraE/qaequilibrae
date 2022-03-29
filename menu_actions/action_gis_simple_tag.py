from ..gis import SimpleTagDialog


def run_tag(qgis_project):
    dlg2 = SimpleTagDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()

