from qgis.PyQt import QtCore


def tr(message):
    """Get string translation."""
    return QtCore.QCoreApplication.translate("AequilibraE", message)
