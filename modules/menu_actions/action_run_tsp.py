from ..routing_procedures import TSPDialog


def run_tsp(qgis_project):
    if qgis_project.project is None:
        qgis_project.show_message_no_project()
    else:
        dlg2 = TSPDialog(qgis_project)
        dlg2.show()
        dlg2.exec_()
