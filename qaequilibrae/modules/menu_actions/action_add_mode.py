def run_add_mode(qgis_project):
    from qaequilibrae.modules.network import AddModeDialog

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    dlg2 = AddModeDialog(qgis_project)
    dlg2.show()
    dlg2.exec()
