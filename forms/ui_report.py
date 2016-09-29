# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_report.ui'
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

class Ui_report(object):
    def setupUi(self, report):
        report.setObjectName(_fromUtf8("report"))
        report.resize(843, 646)
        self.all_data = QtGui.QTextEdit(report)
        self.all_data.setGeometry(QtCore.QRect(0, 0, 843, 605))
        self.all_data.setObjectName(_fromUtf8("all_data"))
        self.pushButton = QtGui.QPushButton(report)
        self.pushButton.setGeometry(QtCore.QRect(10, 610, 821, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.pushButton.setFont(font)
        self.pushButton.setObjectName(_fromUtf8("pushButton"))

        self.retranslateUi(report)
        QtCore.QMetaObject.connectSlotsByName(report)

    def retranslateUi(self, report):
        report.setWindowTitle(_translate("report", "AequilibraE -Algorithm report", None))
        self.pushButton.setText(_translate("report", "Save log", None))

