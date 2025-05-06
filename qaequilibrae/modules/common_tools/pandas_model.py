"""
This class's first version was from https://stackoverflow.com/a/31557937/1480643
and was updated using Matrin Fizpatrick's "Create GUI applications with Python
and PyQt5" code. Please see page 341 for further reference.

According to the author, the code examples in the book are free to use without 
license.
"""

from qgis.PyQt.QtCore import QAbstractTableModel, Qt


class PandasModel(QAbstractTableModel):
    """
    This class populates a table view with a pandas dataframe.
    """

    def __init__(self, data, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._data = data

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        return self._data.shape[1]

    def data(self, index, role):
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self._data.columns[col])
        return None
