from qaequilibrae.i18n.translator import tr


def show_log(qgis_project):
    from ..common_tools import LogDialog
    if qgis_project.project is None:
        qgis_project.iface.messageBar().pushMessage("Error", tr("You need to load a project first"), level=3, duration=10)
        return
    dlg2 = LogDialog(qgis_project)
    dlg2.show()
    dlg2.exec_()
