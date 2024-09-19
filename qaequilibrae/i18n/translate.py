from qgis.PyQt.QtCore import QCoreApplication


def trlt(context, message):
    """ """
    return QCoreApplication.translate(context, message)
