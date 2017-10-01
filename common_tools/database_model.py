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

 Created:    2017-10-30
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import numpy as np
from qgis.core import *
from PyQt4 import QtCore
from PyQt4.QtCore import *
Qt = QtCore.Qt
from auxiliary_functions import logger
    
#This class was adapted from https://www.mail-archive.com/pyqt@riverbankcomputing.com/msg17575.html
#Provided by David Douard

#adaptations for headers come from: http://stackoverflow.com/questions/14135543/how-to-set-the-qtableview-header-name-in-pyqt4

# Adaptations to work with a view of an arbitrary set of fields on a recarray by the author

class DatabaseModel(QtCore.QAbstractTableModel):
    def __init__(self, aeq_dataset, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._array = aeq_dataset
        self.row_headers_data = ['{:,}'.format(x) for x in aeq_dataset.index[:]]

        self.types = []
        self.header_data = []
        for i, n in enumerate(aeq_dataset.data.dtype.names):
            if n in aeq_dataset.fields:
                t = aeq_dataset.data[aeq_dataset.data.dtype.names[i]].dtype
                self.header_data.append(n)
                if np.issubdtype(t, np.integer):
                    self.types.append(0)
                elif np.issubdtype(t, np.float):
                    self.types.append(1)
                else:
                    self.types.append(2)

    def rowCount(self, parent=None):
        return self._array.data.shape[0]

    def columnCount(self, parent=None):
        return len(self.header_data)

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                row = index.row()
                col = index.column()
                """
                TODO:
                Allow user to control display format
                """
                if self.types[col] == 0:
                    return '{:,}'.format(self._array.data[self.header_data[col]][row])
                if self.types[col] == 1:
                    return '{:,.4f}'.format(self._array.data[self.header_data[col]][row])
                else:
                    return str(self._array.data[self.header_data[col]][row])


    def headerData(self, col, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.header_data[col]
        if role == Qt.DisplayRole and orientation != Qt.Horizontal:
            return self.row_headers_data[col]
        
        return QAbstractTableModel.headerData(self, col, orientation, role)
