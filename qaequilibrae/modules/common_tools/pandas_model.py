"""
This class's first version was from https://stackoverflow.com/a/31557937/1480643
and was updated using Matrin Fizpatrick's "Create GUI applications with Python
and PyQt5" code. Please see page 341 for further reference.

According to the author, the code examples in the book are free to use without 
license.
"""

from qgis.PyQt import QtCore


class PandasModel(QtCore.QAbstractTableModel):
    """
    This class populates a table view with a pandas dataframe.
    """

    def __init__(self, data, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._data = data

    def data(self, index, role):
        if index.isValid():
            if role == QtCore.Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, index):
        return self._data.shape[1]

    def header_data(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if orientation == QtCore.Qt.Horizontal:
                return str(self._data.columns[section])
            if orientation == QtCore.Qt.Vertical:
                return str(self._data.index[section])
