# From http://gis.stackexchange.com/questions/45094/how-to-programatically-check-for-a-mouse-click-in-qgis
# By Nathan Woodrow
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.gui import QgsMapTool


class PointTool(QgsMapTool):
    signal = pyqtSignal(object)

    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.point = None
        # QgsMapTool.activate() is what hands this cursor to the canvas, so this class must not
        # override activate(): the empty override it used to carry is why picking a node left
        # the user with whatever cursor the previous map tool had
        self.setCursor(Qt.CursorShape.CrossCursor)

    def canvasReleaseEvent(self, event):
        # Get the click
        x = event.pos().x()
        y = event.pos().y()

        self.point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
        self.signal.emit(1)

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True
