# run method that calls the network preparation section of the code
def run_create_transponet(qgis_project):
    from qaequilibrae.modules.project_procedures import CreatesTranspoNetDialog

    if qgis_project.project is not None:
        qgis_project.message_project_already_open()
        return

    dlg2 = CreatesTranspoNetDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
    # If we wanted modal, we would eliminate the dlg2.show()
