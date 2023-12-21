# This portion of the script initializes the plugin, making it known to QGIS.
def classFactory(iface):
    from .qaequilibrae import AequilibraEMenu

    return AequilibraEMenu(iface)
