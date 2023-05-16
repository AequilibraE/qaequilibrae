def run_shortest_path(qgis_project):
    from .show_shortest_path_dialog import ShortestPathDialog

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    dlg2 = ShortestPathDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
