# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Ui_compare_scenarios.ui'
#
# Created: Fri Dec 02 22:45:31 2016
#      by: PyQt4 UI code generator 4.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from qgis.gui import QgsFieldComboBox, QgsMapLayerComboBox

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

class Ui_compare_scenarios(object):
    def setupUi(self, compare_scenarios):
        compare_scenarios.setObjectName(_fromUtf8("compare_scenarios"))
        compare_scenarios.resize(479, 347)
        self.label = QtGui.QLabel(compare_scenarios)
        self.label.setGeometry(QtCore.QRect(20, 246, 131, 21))
        self.label.setObjectName(_fromUtf8("label"))
        self.label_2 = QtGui.QLabel(compare_scenarios)
        self.label_2.setGeometry(QtCore.QRect(192, 246, 131, 21))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.slider_spacer = QtGui.QSlider(compare_scenarios)
        self.slider_spacer.setGeometry(QtCore.QRect(17, 276, 121, 18))
        self.slider_spacer.setOrientation(QtCore.Qt.Horizontal)
        self.slider_spacer.setObjectName(_fromUtf8("slider_spacer"))
        self.slider_band_size = QtGui.QSlider(compare_scenarios)
        self.slider_band_size.setGeometry(QtCore.QRect(190, 276, 111, 18))
        self.slider_band_size.setOrientation(QtCore.Qt.Horizontal)
        self.slider_band_size.setObjectName(_fromUtf8("slider_band_size"))
        self.mMapLayerComboBox = QgsMapLayerComboBox(compare_scenarios)
        self.mMapLayerComboBox.setGeometry(QtCore.QRect(10, 30, 451, 24))
        self.mMapLayerComboBox.setObjectName(_fromUtf8("mMapLayerComboBox"))
        self.label_3 = QtGui.QLabel(compare_scenarios)
        self.label_3.setGeometry(QtCore.QRect(10, 4, 131, 21))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.but_run = QtGui.QPushButton(compare_scenarios)
        self.but_run.setGeometry(QtCore.QRect(10, 310, 441, 27))
        self.but_run.setObjectName(_fromUtf8("but_run"))
        self.lbl_width = QtGui.QLabel(compare_scenarios)
        self.lbl_width.setGeometry(QtCore.QRect(306, 275, 31, 21))
        self.lbl_width.setObjectName(_fromUtf8("lbl_width"))
        self.lbl_space = QtGui.QLabel(compare_scenarios)
        self.lbl_space.setGeometry(QtCore.QRect(140, 274, 31, 21))
        self.lbl_space.setObjectName(_fromUtf8("lbl_space"))
        self.radio_diff = QtGui.QRadioButton(compare_scenarios)
        self.radio_diff.setGeometry(QtCore.QRect(350, 248, 111, 17))
        self.radio_diff.setChecked(True)
        self.radio_diff.setObjectName(_fromUtf8("radio_diff"))
        self.radio_compo = QtGui.QRadioButton(compare_scenarios)
        self.radio_compo.setGeometry(QtCore.QRect(350, 277, 82, 17))
        self.radio_compo.setObjectName(_fromUtf8("radio_compo"))
        self.groupBox = QtGui.QGroupBox(compare_scenarios)
        self.groupBox.setGeometry(QtCore.QRect(10, 70, 221, 161))
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.ba_FieldComboBoxBase = QgsFieldComboBox(self.groupBox)
        self.ba_FieldComboBoxBase.setGeometry(QtCore.QRect(10, 120, 191, 24))
        self.ba_FieldComboBoxBase.setObjectName(_fromUtf8("ba_FieldComboBoxBase"))
        self.ab_FieldComboBoxBase = QgsFieldComboBox(self.groupBox)
        self.ab_FieldComboBoxBase.setGeometry(QtCore.QRect(10, 60, 191, 24))
        self.ab_FieldComboBoxBase.setObjectName(_fromUtf8("ab_FieldComboBoxBase"))
        self.label_5 = QtGui.QLabel(self.groupBox)
        self.label_5.setGeometry(QtCore.QRect(10, 90, 131, 21))
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.label_6 = QtGui.QLabel(self.groupBox)
        self.label_6.setGeometry(QtCore.QRect(10, 30, 131, 21))
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.groupBox_2 = QtGui.QGroupBox(compare_scenarios)
        self.groupBox_2.setGeometry(QtCore.QRect(240, 70, 221, 161))
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.ba_FieldComboBoxAlt = QgsFieldComboBox(self.groupBox_2)
        self.ba_FieldComboBoxAlt.setGeometry(QtCore.QRect(10, 120, 191, 24))
        self.ba_FieldComboBoxAlt.setObjectName(_fromUtf8("ba_FieldComboBoxAlt"))
        self.ab_FieldComboBoxAlt = QgsFieldComboBox(self.groupBox_2)
        self.ab_FieldComboBoxAlt.setGeometry(QtCore.QRect(10, 60, 191, 24))
        self.ab_FieldComboBoxAlt.setObjectName(_fromUtf8("ab_FieldComboBoxAlt"))
        self.label_9 = QtGui.QLabel(self.groupBox_2)
        self.label_9.setGeometry(QtCore.QRect(10, 90, 131, 21))
        self.label_9.setObjectName(_fromUtf8("label_9"))
        self.label_10 = QtGui.QLabel(self.groupBox_2)
        self.label_10.setGeometry(QtCore.QRect(10, 30, 131, 21))
        self.label_10.setObjectName(_fromUtf8("label_10"))

        self.retranslateUi(compare_scenarios)
        QtCore.QMetaObject.connectSlotsByName(compare_scenarios)

    def retranslateUi(self, compare_scenarios):
        compare_scenarios.setWindowTitle(_translate("compare_scenarios", "Dialog", None))
        self.label.setText(_translate("compare_scenarios", "Space between bands", None))
        self.label_2.setText(_translate("compare_scenarios", "Maximum band width", None))
        self.label_3.setText(_translate("compare_scenarios", "Line layer", None))
        self.but_run.setText(_translate("compare_scenarios", "Create comparison", None))
        self.lbl_width.setText(_translate("compare_scenarios", "1.00", None))
        self.lbl_space.setText(_translate("compare_scenarios", "0.01", None))
        self.radio_diff.setText(_translate("compare_scenarios", "Differences only", None))
        self.radio_compo.setText(_translate("compare_scenarios", "Composite", None))
        self.groupBox.setTitle(_translate("compare_scenarios", "Base case", None))
        self.label_5.setText(_translate("compare_scenarios", "BA Flow", None))
        self.label_6.setText(_translate("compare_scenarios", "AB Flow", None))
        self.groupBox_2.setTitle(_translate("compare_scenarios", "Alternative", None))
        self.label_9.setText(_translate("compare_scenarios", "BA Flow", None))
        self.label_10.setText(_translate("compare_scenarios", "AB Flow", None))
