from PyQt5.QtCore import QAbstractTableModel
from qgis.PyQt.QtCore import Qt


# Largely adapted from http://stackoverflow.com/questions/28033633/using-large-record-set-with-qtableview-and-qabstracttablemodel-retrieve-visib
# Answer by Phil Cooper


class LinkQueryModel(QAbstractTableModel):
    def __init__(self, narray, headerdata, parent=None, *args):
        QAbstractTableModel.__init__(self, parent, *args)
        self._array = narray
        self.headerdata = headerdata

    def rowCount(self, parent):
        return len(self._array)

    def columnCount(self, parent):
        return len(self._array[0])

    def data(self, index, role):
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._array[index.row()][index.column()])

    def headerData(self, col, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headerdata[col]
