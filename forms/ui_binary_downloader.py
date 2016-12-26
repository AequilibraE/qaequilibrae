# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_binary_downloader.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
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

class Ui_binary_downloader(object):
    def setupUi(self, binary_downloader):
        binary_downloader.setObjectName(_fromUtf8("binary_downloader"))
        binary_downloader.resize(675, 267)
        self.label = QtGui.QLabel(binary_downloader)
        self.label.setGeometry(QtCore.QRect(10, 20, 651, 61))
        self.label.setWordWrap(True)
        self.label.setObjectName(_fromUtf8("label"))
        self.lbl_remote_path = QtGui.QLabel(binary_downloader)
        self.lbl_remote_path.setGeometry(QtCore.QRect(10, 90, 651, 17))
        self.lbl_remote_path.setObjectName(_fromUtf8("lbl_remote_path"))
        self.lbl_local_path = QtGui.QLabel(binary_downloader)
        self.lbl_local_path.setGeometry(QtCore.QRect(10, 120, 651, 17))
        self.lbl_local_path.setObjectName(_fromUtf8("lbl_local_path"))
        self.but_download = QtGui.QPushButton(binary_downloader)
        self.but_download.setGeometry(QtCore.QRect(400, 220, 261, 27))
        self.but_download.setObjectName(_fromUtf8("but_download"))
        self.label_2 = QtGui.QLabel(binary_downloader)
        self.label_2.setGeometry(QtCore.QRect(10, 150, 651, 61))
        self.label_2.setWordWrap(True)
        self.label_2.setObjectName(_fromUtf8("label_2"))

        self.retranslateUi(binary_downloader)
        QtCore.QMetaObject.connectSlotsByName(binary_downloader)

    def retranslateUi(self, binary_downloader):
        binary_downloader.setWindowTitle(_translate("binary_downloader", "Binary downloader class", None))
        self.label.setText(_translate("binary_downloader", "To provide fast algorithms, AequilibraE relies on compiled code, which is not allowed in the QGIS plugin repository. To circumvent this  restriction, you need to explicitly agree to download the compiled components of AequilibraE. This operation will only have to be performed once each time you update AequilibraE", None))
        self.lbl_remote_path.setText(_translate("binary_downloader", "File download path:", None))
        self.lbl_local_path.setText(_translate("binary_downloader", "File local destination:", None))
        self.but_download.setText(_translate("binary_downloader", "Agree and download", None))
        self.label_2.setText(_translate("binary_downloader", "The compiled code is also Open Source and has the same license as AequilibraE, and it is included in the repository in the address https://github.com/AequilibraE/AequilibraE", None))

