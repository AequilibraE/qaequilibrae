# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_simple_tag.ui'
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

class Ui_simple_tag(object):
    def setupUi(self, simple_tag):
        simple_tag.setObjectName(_fromUtf8("simple_tag"))
        simple_tag.resize(400, 453)
        font = QtGui.QFont()
        font.setPointSize(9)
        simple_tag.setFont(font)
        self.groupBox = QtGui.QGroupBox(simple_tag)
        self.groupBox.setGeometry(QtCore.QRect(10, 10, 381, 101))
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.fromfield = QtGui.QComboBox(self.groupBox)
        self.fromfield.setGeometry(QtCore.QRect(110, 60, 261, 22))
        self.fromfield.setObjectName(_fromUtf8("fromfield"))
        self.fromlayer = QtGui.QComboBox(self.groupBox)
        self.fromlayer.setGeometry(QtCore.QRect(110, 30, 261, 22))
        self.fromlayer.setObjectName(_fromUtf8("fromlayer"))
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setGeometry(QtCore.QRect(10, 60, 121, 16))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setGeometry(QtCore.QRect(10, 30, 121, 16))
        self.label.setObjectName(_fromUtf8("label"))
        self.groupBox_2 = QtGui.QGroupBox(simple_tag)
        self.groupBox_2.setGeometry(QtCore.QRect(10, 120, 381, 101))
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.tofield = QtGui.QComboBox(self.groupBox_2)
        self.tofield.setGeometry(QtCore.QRect(110, 60, 261, 22))
        self.tofield.setObjectName(_fromUtf8("tofield"))
        self.tolayer = QtGui.QComboBox(self.groupBox_2)
        self.tolayer.setGeometry(QtCore.QRect(110, 30, 261, 22))
        self.tolayer.setObjectName(_fromUtf8("tolayer"))
        self.label_5 = QtGui.QLabel(self.groupBox_2)
        self.label_5.setGeometry(QtCore.QRect(10, 60, 121, 16))
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.label_6 = QtGui.QLabel(self.groupBox_2)
        self.label_6.setGeometry(QtCore.QRect(10, 30, 121, 16))
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.groupBox_3 = QtGui.QGroupBox(simple_tag)
        self.groupBox_3.setGeometry(QtCore.QRect(10, 230, 381, 111))
        self.groupBox_3.setObjectName(_fromUtf8("groupBox_3"))
        self.matchingto = QtGui.QComboBox(self.groupBox_3)
        self.matchingto.setEnabled(True)
        self.matchingto.setGeometry(QtCore.QRect(110, 80, 261, 22))
        self.matchingto.setMaxVisibleItems(10)
        self.matchingto.setObjectName(_fromUtf8("matchingto"))
        self.matchingfrom = QtGui.QComboBox(self.groupBox_3)
        self.matchingfrom.setGeometry(QtCore.QRect(110, 50, 261, 22))
        self.matchingfrom.setMaxVisibleItems(10)
        self.matchingfrom.setObjectName(_fromUtf8("matchingfrom"))
        self.lblmatchto = QtGui.QLabel(self.groupBox_3)
        self.lblmatchto.setGeometry(QtCore.QRect(10, 80, 121, 16))
        self.lblmatchto.setObjectName(_fromUtf8("lblmatchto"))
        self.lblmatchfrom = QtGui.QLabel(self.groupBox_3)
        self.lblmatchfrom.setGeometry(QtCore.QRect(10, 50, 121, 16))
        self.lblmatchfrom.setObjectName(_fromUtf8("lblmatchfrom"))
        self.needsmatching = QtGui.QCheckBox(self.groupBox_3)
        self.needsmatching.setGeometry(QtCore.QRect(10, 20, 221, 17))
        self.needsmatching.setChecked(False)
        self.needsmatching.setObjectName(_fromUtf8("needsmatching"))
        self.groupBox_4 = QtGui.QGroupBox(simple_tag)
        self.groupBox_4.setGeometry(QtCore.QRect(10, 350, 381, 51))
        self.groupBox_4.setObjectName(_fromUtf8("groupBox_4"))
        self.enclosed = QtGui.QRadioButton(self.groupBox_4)
        self.enclosed.setGeometry(QtCore.QRect(10, 20, 71, 17))
        self.enclosed.setChecked(False)
        self.enclosed.setObjectName(_fromUtf8("enclosed"))
        self.touching = QtGui.QRadioButton(self.groupBox_4)
        self.touching.setGeometry(QtCore.QRect(100, 20, 71, 17))
        self.touching.setObjectName(_fromUtf8("touching"))
        self.closest = QtGui.QRadioButton(self.groupBox_4)
        self.closest.setGeometry(QtCore.QRect(180, 20, 61, 17))
        self.closest.setChecked(True)
        self.closest.setObjectName(_fromUtf8("closest"))
        self.progressbar = QtGui.QProgressBar(simple_tag)
        self.progressbar.setGeometry(QtCore.QRect(10, 420, 251, 23))
        self.progressbar.setProperty("value", 0)
        self.progressbar.setObjectName(_fromUtf8("progressbar"))
        self.OK = QtGui.QPushButton(simple_tag)
        self.OK.setGeometry(QtCore.QRect(300, 420, 75, 23))
        self.OK.setObjectName(_fromUtf8("OK"))

        self.retranslateUi(simple_tag)
        QtCore.QMetaObject.connectSlotsByName(simple_tag)

    def retranslateUi(self, simple_tag):
        simple_tag.setWindowTitle(_translate("simple_tag", "AequilibraE  -  Simple TAG", None))
        self.groupBox.setTitle(_translate("simple_tag", "Data source", None))
        self.label_2.setText(_translate("simple_tag", "Data field", None))
        self.label.setText(_translate("simple_tag", "Layer", None))
        self.groupBox_2.setTitle(_translate("simple_tag", "Data destination", None))
        self.label_5.setText(_translate("simple_tag", "Data field", None))
        self.label_6.setText(_translate("simple_tag", "Layer", None))
        self.groupBox_3.setTitle(_translate("simple_tag", "Matching criteria", None))
        self.lblmatchto.setText(_translate("simple_tag", "Destination field", None))
        self.lblmatchfrom.setText(_translate("simple_tag", "Origin field", None))
        self.needsmatching.setText(_translate("simple_tag", "Fields need to have matching values", None))
        self.groupBox_4.setTitle(_translate("simple_tag", "Geographic relation", None))
        self.enclosed.setText(_translate("simple_tag", "Enclosed", None))
        self.touching.setText(_translate("simple_tag", "Touching", None))
        self.closest.setText(_translate("simple_tag", "Closest", None))
        self.OK.setText(_translate("simple_tag", "OK", None))

