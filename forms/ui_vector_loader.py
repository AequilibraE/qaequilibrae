# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_vector_loader.ui'
#
# Created: Sun Oct 23 20:25:39 2016
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

class Ui_vector_loader(object):
    def setupUi(self, vector_loader):
        vector_loader.setObjectName(_fromUtf8("vector_loader"))
        vector_loader.setWindowModality(QtCore.Qt.ApplicationModal)
        vector_loader.resize(456, 197)
        font = QtGui.QFont()
        font.setPointSize(9)
        vector_loader.setFont(font)
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(_fromUtf8("../icon.png")), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        vector_loader.setWindowIcon(icon)
        vector_loader.setModal(True)
        self.load = QtGui.QPushButton(vector_loader)
        self.load.setGeometry(QtCore.QRect(20, 137, 411, 23))
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
        self.progressbar = QtGui.QProgressBar(vector_loader)
        self.progressbar.setEnabled(True)
        self.progressbar.setGeometry(QtCore.QRect(20, 167, 411, 23))
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
        self.field_from = QtGui.QComboBox(vector_loader)
        self.field_from.setGeometry(QtCore.QRect(99, 72, 331, 24))
        self.field_from.setMaxVisibleItems(10)
        self.field_from.setObjectName(_fromUtf8("field_from"))
        self.lbl_matrix = QtGui.QLabel(vector_loader)
        self.lbl_matrix.setGeometry(QtCore.QRect(20, 46, 121, 16))
        self.lbl_matrix.setObjectName(_fromUtf8("lbl_matrix"))
        self.lbl_from = QtGui.QLabel(vector_loader)
        self.lbl_from.setGeometry(QtCore.QRect(20, 76, 121, 16))
        self.lbl_from.setObjectName(_fromUtf8("lbl_from"))
        self.vector_layer = QtGui.QComboBox(vector_loader)
        self.vector_layer.setGeometry(QtCore.QRect(99, 42, 331, 24))
        self.vector_layer.setMaxVisibleItems(10)
        self.vector_layer.setObjectName(_fromUtf8("vector_layer"))
        self.lbl_flow = QtGui.QLabel(vector_loader)
        self.lbl_flow.setGeometry(QtCore.QRect(20, 106, 121, 16))
        self.lbl_flow.setObjectName(_fromUtf8("lbl_flow"))
        self.field_cells = QtGui.QComboBox(vector_loader)
        self.field_cells.setEnabled(True)
        self.field_cells.setGeometry(QtCore.QRect(99, 102, 331, 24))
        self.field_cells.setMaxVisibleItems(10)
        self.field_cells.setObjectName(_fromUtf8("field_cells"))
        self.radio_omx_matrix = QtGui.QRadioButton(vector_loader)
        self.radio_omx_matrix.setGeometry(QtCore.QRect(368, 14, 61, 17))
        self.radio_omx_matrix.setObjectName(_fromUtf8("radio_omx_matrix"))
        self.radio_npy_matrix = QtGui.QRadioButton(vector_loader)
        self.radio_npy_matrix.setGeometry(QtCore.QRect(230, 14, 81, 17))
        self.radio_npy_matrix.setObjectName(_fromUtf8("radio_npy_matrix"))
        self.radio_layer_matrix = QtGui.QRadioButton(vector_loader)
        self.radio_layer_matrix.setGeometry(QtCore.QRect(20, 14, 161, 17))
        self.radio_layer_matrix.setChecked(True)
        self.radio_layer_matrix.setObjectName(_fromUtf8("radio_layer_matrix"))

        self.retranslateUi(vector_loader)
        QtCore.QMetaObject.connectSlotsByName(vector_loader)

    def retranslateUi(self, vector_loader):
        vector_loader.setWindowTitle(_translate("vector_loader", "AequilibraE  -  Vector loader", None))
        self.load.setText(_translate("vector_loader", "LOAD", None))
        self.lbl_matrix.setText(_translate("vector_loader", "File core", None))
        self.lbl_from.setText(_translate("vector_loader", "Zone ID", None))
        self.lbl_flow.setText(_translate("vector_loader", "Flow", None))
        self.radio_omx_matrix.setText(_translate("vector_loader", "OMX", None))
        self.radio_npy_matrix.setText(_translate("vector_loader", "Numpy", None))
        self.radio_layer_matrix.setText(_translate("vector_loader", "Use open file as vector", None))

