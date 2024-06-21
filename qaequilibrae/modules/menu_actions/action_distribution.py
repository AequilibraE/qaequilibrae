def run_distribution_models(qgis_project):
    from qaequilibrae.modules.distribution_procedures import DistributionModelsDialog

    if qgis_project.project is None:
        qgis_project.show_message_no_project()
        return
    dlg2 = DistributionModelsDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
