def run_pt_skim(qgis_project):
    from qaequilibrae.modules.transit_procedures import TransitAssignDialog

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return

    dlg2 = TransitAssignDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
