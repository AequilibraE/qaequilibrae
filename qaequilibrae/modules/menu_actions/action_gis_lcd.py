def run_lcd(qgis_project):
    from qaequilibrae.modules.gis import LeastCommonDenominatorDialog

    dlg2 = LeastCommonDenominatorDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
