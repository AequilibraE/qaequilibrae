from qgis.PyQt.QtCore import QCoreApplication


def tr(text):
    """Get string translation."""
    return QCoreApplication.translate("AequilibraE", text)
