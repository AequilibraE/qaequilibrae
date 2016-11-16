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

    
#This class was adapted from https://www.mail-archive.com/pyqt@riverbankcomputing.com/msg17575.html
#Provided by David Douard

#adaptations for headers come from: http://stackoverflow.com/questions/14135543/how-to-set-the-qtableview-header-name-in-pyqt4

class NumpyModel(QtCore.QAbstractTableModel):
    def __init__(self, narray, headerdata,row_headersdata, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._array = narray
        self.headerdata = headerdata
        self.row_headersdata=row_headersdata

    def rowCount(self, parent=None):
        return self._array.shape[0]

    def columnCount(self, parent=None):
        return self._array.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                row = index.row()
                col = index.column()
                return "%.5f"%self._array[row, col]
                
    def headerData(self, col, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headerdata[col]
        if role == Qt.DisplayRole and orientation != Qt.Horizontal:
            return self.row_headersdata[col]
        
        return QAbstractTableModel.headerData(self, col, orientation, role)
                