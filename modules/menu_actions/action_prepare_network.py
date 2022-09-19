from ..network import NetworkPreparationDialog


def prepare_network(qgis_project):
    dlg2 = NetworkPreparationDialog(qgis_project.iface)
    dlg2.show()
    dlg2.exec_()
