# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_least_common_denominator.ui'
#
# Created: Sun Oct 23 20:28:14 2016
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

class Ui_least_common_denominator(object):
    def setupUi(self, least_common_denominator):
        least_common_denominator.setObjectName(_fromUtf8("least_common_denominator"))
        least_common_denominator.resize(397, 263)
        font = QtGui.QFont()
        font.setPointSize(9)
        least_common_denominator.setFont(font)
        self.groupBox = QtGui.QGroupBox(least_common_denominator)
        self.groupBox.setGeometry(QtCore.QRect(10, 10, 381, 101))
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.fromfield = QtGui.QComboBox(self.groupBox)
        self.fromfield.setGeometry(QtCore.QRect(110, 60, 261, 24))
        self.fromfield.setObjectName(_fromUtf8("fromfield"))
        self.fromlayer = QtGui.QComboBox(self.groupBox)
        self.fromlayer.setGeometry(QtCore.QRect(110, 30, 261, 24))
        self.fromlayer.setObjectName(_fromUtf8("fromlayer"))
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setGeometry(QtCore.QRect(10, 64, 121, 16))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setGeometry(QtCore.QRect(10, 34, 121, 16))
        self.label.setObjectName(_fromUtf8("label"))
        self.groupBox_2 = QtGui.QGroupBox(least_common_denominator)
        self.groupBox_2.setGeometry(QtCore.QRect(10, 120, 381, 101))
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.tofield = QtGui.QComboBox(self.groupBox_2)
        self.tofield.setGeometry(QtCore.QRect(110, 60, 261, 24))
        self.tofield.setObjectName(_fromUtf8("tofield"))
        self.tolayer = QtGui.QComboBox(self.groupBox_2)
        self.tolayer.setGeometry(QtCore.QRect(110, 30, 261, 24))
        self.tolayer.setObjectName(_fromUtf8("tolayer"))
        self.label_5 = QtGui.QLabel(self.groupBox_2)
        self.label_5.setGeometry(QtCore.QRect(10, 65, 121, 16))
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.label_6 = QtGui.QLabel(self.groupBox_2)
        self.label_6.setGeometry(QtCore.QRect(10, 34, 121, 16))
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.progressbar = QtGui.QProgressBar(least_common_denominator)
        self.progressbar.setGeometry(QtCore.QRect(20, 230, 251, 23))
        self.progressbar.setProperty("value", 0)
        self.progressbar.setObjectName(_fromUtf8("progressbar"))
        self.OK = QtGui.QPushButton(least_common_denominator)
        self.OK.setGeometry(QtCore.QRect(310, 230, 75, 23))
        self.OK.setObjectName(_fromUtf8("OK"))

        self.retranslateUi(least_common_denominator)
        QtCore.QMetaObject.connectSlotsByName(least_common_denominator)

    def retranslateUi(self, least_common_denominator):
        least_common_denominator.setWindowTitle(_translate("least_common_denominator", "AequilibraE  -  Least common denominator", None))
        self.groupBox.setTitle(_translate("least_common_denominator", "Layer 1", None))
        self.label_2.setText(_translate("least_common_denominator", "Data field", None))
        self.label.setText(_translate("least_common_denominator", "Layer", None))
        self.groupBox_2.setTitle(_translate("least_common_denominator", "Layer 2", None))
        self.label_5.setText(_translate("least_common_denominator", "Data field", None))
        self.label_6.setText(_translate("least_common_denominator", "Layer", None))
        self.OK.setText(_translate("least_common_denominator", "OK", None))

