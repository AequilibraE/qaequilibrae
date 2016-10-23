# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_gravity_parameters.ui'
#
# Created: Sun Oct 23 20:25:18 2016
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

class Ui_gravity_parameters(object):
    def setupUi(self, gravity_parameters):
        gravity_parameters.setObjectName(_fromUtf8("gravity_parameters"))
        gravity_parameters.resize(308, 85)
        self.label = QtGui.QLabel(gravity_parameters)
        self.label.setGeometry(QtCore.QRect(20, 20, 46, 13))
        self.label.setObjectName(_fromUtf8("label"))
        self.label_2 = QtGui.QLabel(gravity_parameters)
        self.label_2.setGeometry(QtCore.QRect(20, 54, 46, 13))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.alpha_box = QtGui.QPlainTextEdit(gravity_parameters)
        self.alpha_box.setGeometry(QtCore.QRect(60, 15, 121, 25))
        self.alpha_box.setPlainText(_fromUtf8(""))
        self.alpha_box.setObjectName(_fromUtf8("alpha_box"))
        self.beta_box = QtGui.QPlainTextEdit(gravity_parameters)
        self.beta_box.setGeometry(QtCore.QRect(60, 50, 121, 25))
        self.beta_box.setObjectName(_fromUtf8("beta_box"))
        self.but_done = QtGui.QPushButton(gravity_parameters)
        self.but_done.setGeometry(QtCore.QRect(210, 15, 75, 60))
        self.but_done.setObjectName(_fromUtf8("but_done"))

        self.retranslateUi(gravity_parameters)
        QtCore.QMetaObject.connectSlotsByName(gravity_parameters)

    def retranslateUi(self, gravity_parameters):
        gravity_parameters.setWindowTitle(_translate("gravity_parameters", "AequilibraE - Gravity Parameters", None))
        self.label.setText(_translate("gravity_parameters", "Alpha", None))
        self.label_2.setText(_translate("gravity_parameters", "Beta", None))
        self.but_done.setText(_translate("gravity_parameters", "Done", None))

