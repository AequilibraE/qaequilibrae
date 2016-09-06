# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_compute_path.ui'
#
# Created: Mon Sep 05 04:22:13 2016
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

class Ui_compute_path(object):
    def setupUi(self, compute_path):
        compute_path.setObjectName(_fromUtf8("compute_path"))
        compute_path.setWindowModality(QtCore.Qt.NonModal)
        compute_path.resize(170, 115)
        compute_path.setModal(False)
        self.do_dist_matrix = QtGui.QPushButton(compute_path)
        self.do_dist_matrix.setGeometry(QtCore.QRect(10, 90, 151, 21))
        self.do_dist_matrix.setObjectName(_fromUtf8("do_dist_matrix"))
        self.path_to = QtGui.QLineEdit(compute_path)
        self.path_to.setGeometry(QtCore.QRect(60, 63, 100, 20))
        self.path_to.setObjectName(_fromUtf8("path_to"))
        self.to_but = QtGui.QPushButton(compute_path)
        self.to_but.setGeometry(QtCore.QRect(10, 62, 45, 23))
        self.to_but.setObjectName(_fromUtf8("to_but"))
        self.path_from = QtGui.QLineEdit(compute_path)
        self.path_from.setGeometry(QtCore.QRect(60, 33, 100, 20))
        self.path_from.setObjectName(_fromUtf8("path_from"))
        self.from_but = QtGui.QPushButton(compute_path)
        self.from_but.setGeometry(QtCore.QRect(10, 32, 45, 23))
        self.from_but.setObjectName(_fromUtf8("from_but"))
        self.load_graph_from_file = QtGui.QPushButton(compute_path)
        self.load_graph_from_file.setGeometry(QtCore.QRect(10, 3, 151, 21))
        self.load_graph_from_file.setObjectName(_fromUtf8("load_graph_from_file"))

        self.retranslateUi(compute_path)
        QtCore.QMetaObject.connectSlotsByName(compute_path)

    def retranslateUi(self, compute_path):
        compute_path.setWindowTitle(_translate("compute_path", "Shortest path", None))
        self.do_dist_matrix.setText(_translate("compute_path", "Compute", None))
        self.to_but.setText(_translate("compute_path", "To", None))
        self.from_but.setText(_translate("compute_path", "From", None))
        self.load_graph_from_file.setText(_translate("compute_path", "Configure", None))

