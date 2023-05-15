def run_distribution_models(qgis_project):
    from ..distribution_procedures import DistributionModelsDialog
    dlg2 = DistributionModelsDialog(qgis_project.iface)
    dlg2.show()
    dlg2.exec_()
