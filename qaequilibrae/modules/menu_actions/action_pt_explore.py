def run_pt_explore(qgisproject):
    from qaequilibrae.modules.public_transport_procedures.transit_navigator_dialog import TransitNavigatorDialog

    if qgisproject.project is None:
        qgisproject.iface.messageBar().pushMessage("Error", "You need to load a project first", level=3, duration=10)
        return

    dlg2 = TransitNavigatorDialog(qgisproject)
    dlg2.show()
    dlg2.exec_()