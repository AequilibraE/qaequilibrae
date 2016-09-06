# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_matrix_loader.ui'
#
# Created: Tue Sep 06 04:05:22 2016
#      by: PyQt4 UI code generator 4.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_matrix_loader(object):
    def setupUi(self, matrix_loader):
        matrix_loader.setObjectName(_fromUtf8("matrix_loader"))
        matrix_loader.setWindowModality(QtCore.Qt.ApplicationModal)
        matrix_loader.resize(456, 245)
        font = QtGui.QFont()
        font.setPointSize(9)
        matrix_loader.setFont(font)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8("../icon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        matrix_loader.setWindowIcon(icon)
        matrix_loader.setModal(True)
        self.load = QtGui.QPushButton(matrix_loader)
        self.load.setGeometry(QtCore.QRect(20, 172, 411, 23))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(180, 180, 180))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(180, 180, 180))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(180, 180, 180))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        self.load.setPalette(palette)
        self.load.setObjectName(_fromUtf8("load"))
        self.progressbar = QtGui.QProgressBar(matrix_loader)
        self.progressbar.setEnabled(True)
        self.progressbar.setGeometry(QtCore.QRect(20, 202, 411, 23))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(0, 170, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Highlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(240, 240, 240))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Highlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(51, 153, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Highlight, brush)
        self.progressbar.setPalette(palette)
        self.progressbar.setProperty("value", 0)
        self.progressbar.setTextVisible(True)
        self.progressbar.setObjectName(_fromUtf8("progressbar"))
        self.field_cells = QtGui.QComboBox(matrix_loader)
        self.field_cells.setEnabled(True)
        self.field_cells.setGeometry(QtCore.QRect(89, 132, 341, 22))
        self.field_cells.setMaxVisibleItems(10)
        self.field_cells.setObjectName(_fromUtf8("field_cells"))
        self.field_from = QtGui.QComboBox(matrix_loader)
        self.field_from.setGeometry(QtCore.QRect(89, 72, 341, 22))
        self.field_from.setMaxVisibleItems(10)
        self.field_from.setObjectName(_fromUtf8("field_from"))
        self.lbl_matrix = QtGui.QLabel(matrix_loader)
        self.lbl_matrix.setGeometry(QtCore.QRect(20, 42, 121, 16))
        self.lbl_matrix.setObjectName(_fromUtf8("lbl_matrix"))
        self.lbl_from = QtGui.QLabel(matrix_loader)
        self.lbl_from.setGeometry(QtCore.QRect(20, 72, 121, 16))
        self.lbl_from.setObjectName(_fromUtf8("lbl_from"))
        self.lbl_flow = QtGui.QLabel(matrix_loader)
        self.lbl_flow.setGeometry(QtCore.QRect(20, 132, 121, 16))
        self.lbl_flow.setObjectName(_fromUtf8("lbl_flow"))
        self.matrix_layer = QtGui.QComboBox(matrix_loader)
        self.matrix_layer.setGeometry(QtCore.QRect(89, 42, 341, 22))
        self.matrix_layer.setMaxVisibleItems(10)
        self.matrix_layer.setObjectName(_fromUtf8("matrix_layer"))
        self.lbl_to = QtGui.QLabel(matrix_loader)
        self.lbl_to.setGeometry(QtCore.QRect(20, 102, 121, 16))
        self.lbl_to.setObjectName(_fromUtf8("lbl_to"))
        self.field_to = QtGui.QComboBox(matrix_loader)
        self.field_to.setEnabled(True)
        self.field_to.setGeometry(QtCore.QRect(89, 102, 341, 22))
        self.field_to.setMaxVisibleItems(10)
        self.field_to.setObjectName(_fromUtf8("field_to"))
        self.radio_omx_matrix = QtGui.QRadioButton(matrix_loader)
        self.radio_omx_matrix.setGeometry(QtCore.QRect(368, 14, 61, 17))
        self.radio_omx_matrix.setObjectName(_fromUtf8("radio_omx_matrix"))
        self.radio_npy_matrix = QtGui.QRadioButton(matrix_loader)
        self.radio_npy_matrix.setGeometry(QtCore.QRect(230, 14, 61, 17))
        self.radio_npy_matrix.setObjectName(_fromUtf8("radio_npy_matrix"))
        self.radio_layer_matrix = QtGui.QRadioButton(matrix_loader)
        self.radio_layer_matrix.setGeometry(QtCore.QRect(20, 14, 151, 17))
        self.radio_layer_matrix.setChecked(True)
        self.radio_layer_matrix.setObjectName(_fromUtf8("radio_layer_matrix"))

        self.retranslateUi(matrix_loader)
        QtCore.QMetaObject.connectSlotsByName(matrix_loader)

    def retranslateUi(self, matrix_loader):
        matrix_loader.setWindowTitle(_translate("matrix_loader", "AequilibraE  -  Matrix loader", None))
        self.load.setText(_translate("matrix_loader", "LOAD", None))
        self.lbl_matrix.setText(_translate("matrix_loader", "Matrix", None))
        self.lbl_from.setText(_translate("matrix_loader", "From", None))
        self.lbl_flow.setText(_translate("matrix_loader", "Flow", None))
        self.lbl_to.setText(_translate("matrix_loader", "To", None))
        self.radio_omx_matrix.setText(_translate("matrix_loader", "OMX", None))
        self.radio_npy_matrix.setText(_translate("matrix_loader", "Numpy", None))
        self.radio_layer_matrix.setText(_translate("matrix_loader", "Use open file as matrix", None))

