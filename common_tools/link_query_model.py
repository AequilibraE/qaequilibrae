"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       NumPy Model
 Purpose:    Loads numpy to a GUI in an efficient fashion

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2014-03-19
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
from PyQt4 import QtCore
from PyQt4.QtCore import *
Qt = QtCore.Qt

    
# Largely adapted from http://stackoverflow.com/questions/28033633/using-large-record-set-with-qtableview-and-qabstracttablemodel-retrieve-visib
#Answer by Phil Cooper

class LinkQueryModel(QtCore.QAbstractTableModel):
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
            if  role == Qt.DisplayRole:
                return str(self._array[index.row()][index.column()])

    def headerData(self, col, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headerdata[col]