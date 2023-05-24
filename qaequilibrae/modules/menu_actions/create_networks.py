

# run method that calls the network preparation section of the code
def run_create_transponet(qgisproject):
    from ..project_procedures import CreatesTranspoNetDialog
    if qgisproject.project is not None:
        qgisproject.message_project_already_open()
        return

    dlg2 = CreatesTranspoNetDialog(qgisproject)
    dlg2.show()
    dlg2.exec_()
    # If we wanted modal, we would eliminate the dlg2.show()
