from ..gis import CreateBandwidthsDialog


def run_stacked_bandwidths(qgis_project):
    dlg2 = CreateBandwidthsDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
