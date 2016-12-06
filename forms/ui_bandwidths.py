# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_bandwidths.ui'
#
# Created by: PyQt4 UI code generator 4.11.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui
from qgis.gui  import QgsColorButtonV2, QgsFieldComboBox, QgsMapLayerComboBox

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

class Ui_bandwidths(object):
    def setupUi(self, bandwidths):
        bandwidths.setObjectName(_fromUtf8("bandwidths"))
        bandwidths.resize(689, 362)
        self.label = QtGui.QLabel(bandwidths)
        self.label.setGeometry(QtCore.QRect(20, 10, 131, 21))
        self.label.setObjectName(_fromUtf8("label"))
        self.label_2 = QtGui.QLabel(bandwidths)
        self.label_2.setGeometry(QtCore.QRect(200, 10, 131, 21))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.slider_spacer = QtGui.QSlider(bandwidths)
        self.slider_spacer.setGeometry(QtCore.QRect(17, 40, 121, 18))
        self.slider_spacer.setOrientation(QtCore.Qt.Horizontal)
        self.slider_spacer.setObjectName(_fromUtf8("slider_spacer"))
        self.slider_band_size = QtGui.QSlider(bandwidths)
        self.slider_band_size.setGeometry(QtCore.QRect(198, 40, 111, 18))
        self.slider_band_size.setOrientation(QtCore.Qt.Horizontal)
        self.slider_band_size.setObjectName(_fromUtf8("slider_band_size"))
        self.mMapLayerComboBox = QgsMapLayerComboBox(bandwidths)
        self.mMapLayerComboBox.setGeometry(QtCore.QRect(380, 30, 301, 30))
        self.mMapLayerComboBox.setObjectName(_fromUtf8("mMapLayerComboBox"))
        self.ab_FieldComboBox = QgsFieldComboBox(bandwidths)
        self.ab_FieldComboBox.setGeometry(QtCore.QRect(20, 92, 191, 30))
        self.ab_FieldComboBox.setObjectName(_fromUtf8("ab_FieldComboBox"))
        self.mColorButton = QgsColorButtonV2(bandwidths)
        self.mColorButton.setGeometry(QtCore.QRect(430, 92, 141, 30))
        self.mColorButton.setObjectName(_fromUtf8("mColorButton"))
        self.label_3 = QtGui.QLabel(bandwidths)
        self.label_3.setGeometry(QtCore.QRect(380, 10, 131, 21))
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.ba_FieldComboBox = QgsFieldComboBox(bandwidths)
        self.ba_FieldComboBox.setGeometry(QtCore.QRect(224, 92, 191, 30))
        self.ba_FieldComboBox.setObjectName(_fromUtf8("ba_FieldComboBox"))
        self.but_add_band = QtGui.QPushButton(bandwidths)
        self.but_add_band.setGeometry(QtCore.QRect(610, 92, 71, 30))
        self.but_add_band.setObjectName(_fromUtf8("but_add_band"))
        self.bands_list = QtGui.QTableWidget(bandwidths)
        self.bands_list.setGeometry(QtCore.QRect(10, 140, 671, 181))
        self.bands_list.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.bands_list.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.bands_list.setRowCount(0)
        self.bands_list.setColumnCount(4)
        self.bands_list.setObjectName(_fromUtf8("bands_list"))
        item = QtGui.QTableWidgetItem()
        self.bands_list.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.bands_list.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        self.bands_list.setHorizontalHeaderItem(2, item)
        item = QtGui.QTableWidgetItem()
        self.bands_list.setHorizontalHeaderItem(3, item)
        self.bands_list.verticalHeader().setDefaultSectionSize(27)
        self.label_5 = QtGui.QLabel(bandwidths)
        self.label_5.setGeometry(QtCore.QRect(224, 70, 131, 21))
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.label_6 = QtGui.QLabel(bandwidths)
        self.label_6.setGeometry(QtCore.QRect(20, 70, 131, 21))
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.but_run = QtGui.QPushButton(bandwidths)
        self.but_run.setGeometry(QtCore.QRect(10, 330, 671, 27))
        self.but_run.setObjectName(_fromUtf8("but_run"))
        self.lbl_width = QtGui.QLabel(bandwidths)
        self.lbl_width.setGeometry(QtCore.QRect(314, 39, 31, 21))
        self.lbl_width.setObjectName(_fromUtf8("lbl_width"))
        self.lbl_space = QtGui.QLabel(bandwidths)
        self.lbl_space.setGeometry(QtCore.QRect(140, 38, 31, 21))
        self.lbl_space.setObjectName(_fromUtf8("lbl_space"))
        self.but_load_ramp = QtGui.QPushButton(bandwidths)
        self.but_load_ramp.setGeometry(QtCore.QRect(541, 92, 61, 30))
        self.but_load_ramp.setObjectName(_fromUtf8("but_load_ramp"))
        self.rdo_color = QtGui.QRadioButton(bandwidths)
        self.rdo_color.setGeometry(QtCore.QRect(426, 70, 101, 22))
        self.rdo_color.setChecked(True)
        self.rdo_color.setObjectName(_fromUtf8("rdo_color"))
        self.rdo_ramp = QtGui.QRadioButton(bandwidths)
        self.rdo_ramp.setGeometry(QtCore.QRect(515, 70, 91, 22))
        self.rdo_ramp.setObjectName(_fromUtf8("rdo_ramp"))
        self.txt_ramp = QtGui.QLabel(bandwidths)
        self.txt_ramp.setGeometry(QtCore.QRect(430, 98, 101, 17))
        self.txt_ramp.setObjectName(_fromUtf8("txt_ramp"))

        self.retranslateUi(bandwidths)
        QtCore.QMetaObject.connectSlotsByName(bandwidths)

    def retranslateUi(self, bandwidths):
        bandwidths.setWindowTitle(_translate("bandwidths", "Dialog", None))
        self.label.setText(_translate("bandwidths", "Space between bands", None))
        self.label_2.setText(_translate("bandwidths", "Maximum band width", None))
        self.label_3.setText(_translate("bandwidths", "Line layer", None))
        self.but_add_band.setText(_translate("bandwidths", "Add band", None))
        self.bands_list.setAccessibleName(_translate("bandwidths", "<html><head/><body><p>xcxc</p></body></html>", None))
        item = self.bands_list.horizontalHeaderItem(0)
        item.setText(_translate("bandwidths", "AB flow", None))
        item = self.bands_list.horizontalHeaderItem(1)
        item.setText(_translate("bandwidths", "BA Flow", None))
        item = self.bands_list.horizontalHeaderItem(2)
        item.setText(_translate("bandwidths", "Color", None))
        item = self.bands_list.horizontalHeaderItem(3)
        item.setText(_translate("bandwidths", "Move/delete", None))
        self.label_5.setText(_translate("bandwidths", "BA Flow", None))
        self.label_6.setText(_translate("bandwidths", "AB Flow", None))
        self.but_run.setText(_translate("bandwidths", "Create bands", None))
        self.lbl_width.setText(_translate("bandwidths", "1.00", None))
        self.lbl_space.setText(_translate("bandwidths", "0.01", None))
        self.but_load_ramp.setText(_translate("bandwidths", "Ramp", None))
        self.rdo_color.setText(_translate("bandwidths", "Solid color", None))
        self.rdo_ramp.setText(_translate("bandwidths", "Color ramp", None))
        self.txt_ramp.setText(_translate("bandwidths", "...", None))
