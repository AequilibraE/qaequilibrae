# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_parameters.ui'
#
# Created: Sun Aug 14 17:56:33 2016
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

class Ui_parameters(object):
    def setupUi(self, parameters):
        parameters.setObjectName(_fromUtf8("parameters"))
        parameters.resize(701, 487)
        self.but_save = QtGui.QPushButton(parameters)
        self.but_save.setGeometry(QtCore.QRect(115, 450, 101, 23))
        self.but_save.setObjectName(_fromUtf8("but_save"))
        self.but_close = QtGui.QPushButton(parameters)
        self.but_close.setGeometry(QtCore.QRect(580, 450, 101, 23))
        self.but_close.setObjectName(_fromUtf8("but_close"))
        self.text_box = Qsci.QsciScintilla(parameters)
        self.text_box.setGeometry(QtCore.QRect(10, 10, 681, 431))
        self.text_box.setToolTip(_fromUtf8(""))
        self.text_box.setWhatsThis(_fromUtf8(""))
        self.text_box.setObjectName(_fromUtf8("text_box"))
        self.but_validate = QtGui.QPushButton(parameters)
        self.but_validate.setGeometry(QtCore.QRect(10, 450, 101, 23))
        self.but_validate.setObjectName(_fromUtf8("but_validate"))
        self.but_defaults = QtGui.QPushButton(parameters)
        self.but_defaults.setGeometry(QtCore.QRect(470, 450, 101, 23))
        self.but_defaults.setObjectName(_fromUtf8("but_defaults"))

        self.retranslateUi(parameters)
        QtCore.QMetaObject.connectSlotsByName(parameters)

    def retranslateUi(self, parameters):
        parameters.setWindowTitle(_translate("parameters", "AequilibraE - Parameters", None))
        self.but_save.setText(_translate("parameters", "Save to disk", None))
        self.but_close.setText(_translate("parameters", "Cancel and close", None))
        self.but_validate.setText(_translate("parameters", "Validate", None))
        self.but_defaults.setText(_translate("parameters", "Reset to defaults", None))

from PyQt4 import Qsci
