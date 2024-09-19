def show_log(qgis_project):
    from qaequilibrae.modules.common_tools import LogDialog

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return
    dlg2 = LogDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
