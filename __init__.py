# This portion of the script initializes the plugin, making it known to QGIS.
def classFactory(iface):
    from .aequilibrae_menu import AequilibraEMenu
    return AequilibraEMenu(iface)
