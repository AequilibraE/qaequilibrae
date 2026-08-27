def run_add_link_type(qgis_project):
    from qaequilibrae.modules.network import AddLinkTypeDialog

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    dlg2 = AddLinkTypeDialog(qgis_project)
    dlg2.show()
    dlg2.exec()
