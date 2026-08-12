def run_desire_lines(qgis_project):
    from qaequilibrae.modules.gis.desire_lines_dialog import DesireLinesDialog

    dlg2 = DesireLinesDialog(qgis_project)
    dlg2.show()
    dlg2.exec()
