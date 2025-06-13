def load_isochrones(qgis_project):
    from qaequilibrae.modules.paths_procedures.isochrones_dialog import IsochronesDialog

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    dlg2 = IsochronesDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
