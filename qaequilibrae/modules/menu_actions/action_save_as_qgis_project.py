def save_as_qgis_project(qgis_project):
    from qaequilibrae.modules.menu_actions.save_as_qgis import SaveAsQGZ

    if qgis_project.project is None:
        qgis_project.iface.messageBar().pushMessage("Error", "You need to load a project first", level=3, duration=10)
        return

    SaveAsQGZ(qgis_project)
