from modules.gis import LeastCommonDenominatorDialog


def run_lcd(qgis_project):
    dlg2 = LeastCommonDenominatorDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
