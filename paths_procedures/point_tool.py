# From http://gis.stackexchange.com/questions/45094/how-to-programatically-check-for-a-mouse-click-in-qgis
# By Nathan Woodrow
from qgis.gui import QgsMapTool
from PyQt5.QtCore import pyqtSignal


class PointTool(QgsMapTool):
    clicked = pyqtSignal(object)

    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas

    def canvasPressEvent(self, event):
        x = event.pos().x()
        y = event.pos().y()

        _ = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)

    def canvasMoveEvent(self, event):
        x = event.pos().x()
        y = event.pos().y()

        _ = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)

    def canvasReleaseEvent(self, event):
        # Get the click
        x = event.pos().x()
        y = event.pos().y()

        self.point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
        self.clicked.emit(1)

    def activate(self):
        pass

    def deactivate(self):
        pass

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True
