def run_desire_lines(qgis_project):
    from ..gis.desire_lines_dialog import DesireLinesDialog
    # if qgis_project.project is None:
    #     qgis_project.iface.messageBar().pushMessage("Error", "You need to load a project first", level=3, duration=10)
    #     return

    dlg2 = DesireLinesDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
