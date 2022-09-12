from ..distribution_procedures import DistributionModelsDialog


def run_distribution_models(qgis_project):
    dlg2 = DistributionModelsDialog(qgis_project.iface)
    dlg2.show()
    dlg2.exec_()
