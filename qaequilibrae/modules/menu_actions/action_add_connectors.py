def run_add_connectors(qgis_project):
    from qaequilibrae.modules.network import AddConnectorsDialog

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return
    dlg2 = AddConnectorsDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
