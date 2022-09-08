import numpy as np

import qgis
from qgis.PyQt import QtWidgets, uic, QtCore
from qgis.PyQt.QtCore import *

Qt = QtCore.Qt


# This class was adapted from https://www.mail-archive.com/pyqt@riverbankcomputing.com/msg17575.html
# Provided by David Douard

# adaptations for headers come from: http://stackoverflow.com/questions/14135543/how-to-set-the-qtableview-header-name-in-pyqt4


class NumpyModel(QtCore.QAbstractTableModel):
    def __init__(self, aeq_matrix, separator, decimals, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._array = aeq_matrix
        self.separator = separator
        self.decimals = decimals
        if self.separator:
            self.row_headers_data = ["{:,}".format(x) for x in aeq_matrix.index[:]]
            self.header_data = ["{:,}".format(x) for x in aeq_matrix.index[:]]
        else:
            self.row_headers_data = [str(x) for x in aeq_matrix.index[:]]
            self.header_data = [str(x) for x in aeq_matrix.index[:]]

        if np.issubdtype(aeq_matrix.dtype, np.integer):
            self.empties = np.iinfo(aeq_matrix.dtype).min
            self.decimals = 0

    def rowCount(self, parent=None):
        if self._array.matrix_view is None:
            return 0
        else:
            return self._array.matrix_view.shape[0]

    def columnCount(self, parent=None):
        if self._array.matrix_view is None:
            return 0
        else:
            return self._array.matrix_view.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                row = index.row()
                col = index.column()

                separator = ""
                if self.separator:
                    separator = ","

                if np.issubdtype(self._array.dtype, np.integer):
                    if self._array.matrix_view[row, col] == self.empties:
                        return ""
                    else:
                        return ("{:" + separator + "." + str(self.decimals) + "f}").format(
                            self._array.matrix_view[row, col]
                        )
                else:
                    if np.isnan(self._array.matrix_view[row, col]):
                        return ""
                    else:
                        return ("{:" + separator + "." + str(self.decimals) + "f}").format(
                            self._array.matrix_view[row, col]
                        )

    def headerData(self, col, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.header_data[col]
        if role == Qt.DisplayRole and orientation != Qt.Horizontal:
            return self.row_headers_data[col]

        return QtCore.QAbstractTableModel.headerData(self, col, orientation, role)
