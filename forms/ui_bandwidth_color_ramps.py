# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_bandwidth_color_ramps.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from qgis.gui import QgsFieldComboBox
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

class Ui_BandwidthColorRamps(object):
    def setupUi(self, BandwidthColorRamps):
        BandwidthColorRamps.setObjectName(_fromUtf8("BandwidthColorRamps"))
        BandwidthColorRamps.resize(589, 238)
        self.chk_dual_fields = QtGui.QCheckBox(BandwidthColorRamps)
        self.chk_dual_fields.setGeometry(QtCore.QRect(10, 10, 88, 22))
        self.chk_dual_fields.setChecked(True)
        self.chk_dual_fields.setObjectName(_fromUtf8("chk_dual_fields"))
        self.txt_ab_min = QtGui.QLineEdit(BandwidthColorRamps)
        self.txt_ab_min.setGeometry(QtCore.QRect(115, 130, 80, 28))
        self.txt_ab_min.setObjectName(_fromUtf8("txt_ab_min"))
        self.txt_ab_max = QtGui.QLineEdit(BandwidthColorRamps)
        self.txt_ab_max.setGeometry(QtCore.QRect(239, 130, 80, 28))
        self.txt_ab_max.setObjectName(_fromUtf8("txt_ab_max"))
        self.label = QtGui.QLabel(BandwidthColorRamps)
        self.label.setGeometry(QtCore.QRect(210, 135, 31, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setItalic(True)
        font.setWeight(75)
        self.label.setFont(font)
        self.label.setObjectName(_fromUtf8("label"))
        self.label_2 = QtGui.QLabel(BandwidthColorRamps)
        self.label_2.setGeometry(QtCore.QRect(86, 136, 31, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setItalic(True)
        font.setWeight(75)
        self.label_2.setFont(font)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.label_3 = QtGui.QLabel(BandwidthColorRamps)
        self.label_3.setEnabled(False)
        self.label_3.setGeometry(QtCore.QRect(348, 135, 31, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setItalic(True)
        font.setWeight(75)
        self.label_3.setFont(font)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.txt_ba_min = QtGui.QLineEdit(BandwidthColorRamps)
        self.txt_ba_min.setEnabled(False)
        self.txt_ba_min.setGeometry(QtCore.QRect(380, 130, 80, 28))
        self.txt_ba_min.setObjectName(_fromUtf8("txt_ba_min"))
        self.label_4 = QtGui.QLabel(BandwidthColorRamps)
        self.label_4.setEnabled(False)
        self.label_4.setGeometry(QtCore.QRect(470, 135, 31, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setItalic(True)
        font.setWeight(75)
        self.label_4.setFont(font)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.txt_ba_max = QtGui.QLineEdit(BandwidthColorRamps)
        self.txt_ba_max.setEnabled(False)
        self.txt_ba_max.setGeometry(QtCore.QRect(500, 130, 80, 28))
        self.txt_ba_max.setObjectName(_fromUtf8("txt_ba_max"))
        self.cbb_ab_color = QtGui.QComboBox(BandwidthColorRamps)
        self.cbb_ab_color.setGeometry(QtCore.QRect(80, 90, 238, 28))
        self.cbb_ab_color.setObjectName(_fromUtf8("cbb_ab_color"))
        self.cbb_ba_color = QtGui.QComboBox(BandwidthColorRamps)
        self.cbb_ba_color.setEnabled(False)
        self.cbb_ba_color.setGeometry(QtCore.QRect(344, 90, 238, 28))
        self.cbb_ba_color.setObjectName(_fromUtf8("cbb_ba_color"))
        self.label_5 = QtGui.QLabel(BandwidthColorRamps)
        self.label_5.setGeometry(QtCore.QRect(45, 55, 31, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.label_5.setFont(font)
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.label_6 = QtGui.QLabel(BandwidthColorRamps)
        self.label_6.setGeometry(QtCore.QRect(8, 94, 81, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.label_6.setFont(font)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.but_cancel = QtGui.QPushButton(BandwidthColorRamps)
        self.but_cancel.setGeometry(QtCore.QRect(145, 200, 85, 27))
        self.but_cancel.setObjectName(_fromUtf8("but_cancel"))
        self.but_done = QtGui.QPushButton(BandwidthColorRamps)
        self.but_done.setGeometry(QtCore.QRect(45, 200, 85, 27))
        self.but_done.setObjectName(_fromUtf8("but_done"))
        self.cbb_ba_field = QgsFieldComboBox(BandwidthColorRamps)
        self.cbb_ba_field.setGeometry(QtCore.QRect(344, 50, 238, 28))
        self.cbb_ba_field.setObjectName(_fromUtf8("cbb_ba_field"))
        self.cbb_ab_field = QtGui.QComboBox(BandwidthColorRamps)
        self.cbb_ab_field.setGeometry(QtCore.QRect(80, 50, 238, 28))
        self.cbb_ab_field.setObjectName(_fromUtf8("cbb_ab_field"))

        self.retranslateUi(BandwidthColorRamps)
        QtCore.QMetaObject.connectSlotsByName(BandwidthColorRamps)

    def retranslateUi(self, BandwidthColorRamps):
        BandwidthColorRamps.setWindowTitle(_translate("BandwidthColorRamps", "Dialog", None))
        self.chk_dual_fields.setText(_translate("BandwidthColorRamps", "Dual fields", None))
        self.label.setText(_translate("BandwidthColorRamps", "Max", None))
        self.label_2.setText(_translate("BandwidthColorRamps", "Min", None))
        self.label_3.setText(_translate("BandwidthColorRamps", "Min", None))
        self.label_4.setText(_translate("BandwidthColorRamps", "Max", None))
        self.label_5.setText(_translate("BandwidthColorRamps", "Field", None))
        self.label_6.setText(_translate("BandwidthColorRamps", "Color ramp", None))
        self.but_cancel.setText(_translate("BandwidthColorRamps", "Cancel", None))
        self.but_done.setText(_translate("BandwidthColorRamps", "Done", None))


