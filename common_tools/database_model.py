"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Database Model
 Purpose:    Loads numpy recarray to a GUI in an efficient fashion

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com1
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2017-10-02
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import numpy as np
from qgis.PyQt import QtCore

Qt = QtCore.Qt

# This class was adapted from https://www.mail-archive.com/pyqt@riverbankcomputing.com/msg17575.html
# Provided by David Douard

# Adaptations for headers come from:
#           http://stackoverflow.com/questions/14135543/how-to-set-the-qtableview-header-name-in-pyqt4
# Adaptations to work with a view of an arbitrary set of fields on a recarray by the author


class DatabaseModel(QtCore.QAbstractTableModel):
    def __init__(self, aeq_dataset, separator, decimals, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._array = aeq_dataset
        self.separator = separator
        self.decimals = decimals
        if self.separator:
            self.row_headers_data = ["{:,}".format(x) for x in aeq_dataset.index[:]]
        else:
            self.row_headers_data = [str(x) for x in aeq_dataset.index[:]]

        self.empties = []
        self.types = []
        self.header_data = []
        for i, n in enumerate(aeq_dataset.data.dtype.names):
            if n in aeq_dataset.fields:
                t = aeq_dataset.data[aeq_dataset.data.dtype.names[i]].dtype
                self.header_data.append(n)
                # noinspection PyUnresolvedReferences
                if np.issubdtype(t, np.integer):
                    self.types.append(0)
                    self.empties.append(np.iinfo(t).min)
                elif np.issubdtype(t, np.float):
                    self.types.append(1)
                    self.empties.append(np.nan)
                else:
                    self.types.append(2)
                    self.empties.append("")

    def rowCount(self, parent=None):
        return self._array.data.shape[0]

    def columnCount(self, parent=None):
        return len(self.header_data)

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                row = index.row()
                col = index.column()

                if self.separator:
                    if self.types[col] == 0:
                        if self._array.data[self.header_data[col]][row] == self.empties[col]:
                            return ""
                        else:
                            return "{:,}".format(self._array.data[self.header_data[col]][row])
                    if self.types[col] == 1:
                        if self._array.data[self.header_data[col]][row] == self.empties[col]:
                            return ""
                        else:
                            return ("{:,." + str(self.decimals) + "f}").format(
                                self._array.data[self.header_data[col]][row]
                            )
                    else:
                        return str(self._array.data[self.header_data[col]][row])
                else:
                    if self.types[col] == 0:
                        if self._array.data[self.header_data[col]][row] == self.empties[col]:
                            return ""
                        else:
                            return "{:}".format(self._array.data[self.header_data[col]][row])
                    if self.types[col] == 1:
                        if self._array.data[self.header_data[col]][row] == self.empties[col]:
                            return ""
                        else:
                            return ("{:." + str(self.decimals) + "f}").format(
                                self._array.data[self.header_data[col]][row]
                            )
                    else:
                        return str(self._array.data[self.header_data[col]][row])

    def headerData(self, col, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.header_data[col]
        if role == Qt.DisplayRole and orientation != Qt.Horizontal:
            return self.row_headers_data[col]

        return QtCore.QAbstractTableModel.headerData(self, col, orientation, role)
