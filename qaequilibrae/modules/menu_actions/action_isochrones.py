def load_skim_viewer(qgis_project):
    from qaequilibrae.modules.paths_procedures.skim_viewer_dialog import SkimViewerDialog

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    dlg2 = SkimViewerDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
