# This portion of the script initializes the plugin, making it known to QGIS.
def classFactory(iface):
    from .qaequilibrae import AequilibraEMenu

    return AequilibraEMenu(iface)


# Global variable to hold the AequilibraEMenu instance
_aequilibrae_menu_instance = None


def set_aequilibrae_menu_instance(menu_instance):
    """Set the global AequilibraEMenu instance"""
    global _aequilibrae_menu_instance
    _aequilibrae_menu_instance = menu_instance


def get_aequilibrae_menu_instance():
    """Get the global AequilibraEMenu instance"""
    global _aequilibrae_menu_instance
    return _aequilibrae_menu_instance
