from modules.gis import CompareScenariosDialog


def run_scenario_comparison(qgis_project):
    if qgis_project.project is None:
        qgis_project.iface.messageBar().pushMessage("Error", "You need to load a project first", level=3, duration=10)
        return

    dlg2 = CompareScenariosDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
