def run_tag(qgis_project):
    from qaequilibrae.modules.gis import SimpleTagDialog

    dlg2 = SimpleTagDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
