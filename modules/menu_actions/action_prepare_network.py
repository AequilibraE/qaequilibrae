def prepare_network(qgis_project):
    from ..network import NetworkPreparationDialog
    dlg2 = NetworkPreparationDialog(qgis_project.iface)
    dlg2.show()
    dlg2.exec_()
