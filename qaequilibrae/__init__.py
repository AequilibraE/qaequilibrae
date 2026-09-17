class _HeadlessProcessingPlugin:
    """QGIS plugin wrapper used by ``qgis_process``.

    The normal plugin entry point builds the Desktop menu and dock widget.  A processing
    application has no ``iface``, so it needs a provider-only entry point instead.
    """

    def __init__(self):
        import sys
        from pathlib import Path

        from qgis.core import QgsApplication

        packages = Path(__file__).parent / "packages"
        if str(packages) not in sys.path:
            sys.path.insert(0, str(packages))

        from .modules.processing_provider.provider import HeadlessProvider

        self._registry = QgsApplication.processingRegistry()
        self._provider = HeadlessProvider()

    def initGui(self):
        """Satisfy the QGIS plugin lifecycle without creating GUI objects."""
        self.initProcessing()

    def initProcessing(self):
        """Register the provider for QGIS Processing-only plugin startup."""
        if self._provider not in self._registry.providers():
            self._registry.addProvider(self._provider)

    def unload(self):
        if self._provider in self._registry.providers():
            self._registry.removeProvider(self._provider)


# This portion of the script initializes the plugin, making it known to QGIS.
def classFactory(iface):
    if iface is None:
        return _HeadlessProcessingPlugin()

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
