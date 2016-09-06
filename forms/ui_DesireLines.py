# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_DesireLines.ui'
#
# Created: Tue Sep 06 04:16:52 2016
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

class Ui_DesireLines(object):
    def setupUi(self, DesireLines):
        DesireLines.setObjectName(_fromUtf8("DesireLines"))
        DesireLines.setWindowModality(QtCore.Qt.ApplicationModal)
        DesireLines.resize(643, 593)
        DesireLines.setModal(True)
        self.lbl_funding2 = QtGui.QLabel(DesireLines)
        self.lbl_funding2.setGeometry(QtCore.QRect(530, 570, 91, 21))
        font = QtGui.QFont()
        font.setPointSize(7)
        font.setBold(True)
        font.setWeight(75)
        self.lbl_funding2.setFont(font)
        self.lbl_funding2.setTextFormat(QtCore.Qt.PlainText)
        self.lbl_funding2.setObjectName(_fromUtf8("lbl_funding2"))
        self.lbl_funding1 = QtGui.QLabel(DesireLines)
        self.lbl_funding1.setGeometry(QtCore.QRect(450, 573, 91, 16))
        font = QtGui.QFont()
        font.setPointSize(7)
        self.lbl_funding1.setFont(font)
        self.lbl_funding1.setObjectName(_fromUtf8("lbl_funding1"))
        self.progressbar = QtGui.QProgressBar(DesireLines)
        self.progressbar.setEnabled(True)
        self.progressbar.setGeometry(QtCore.QRect(10, 566, 251, 23))
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(0, 170, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Highlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(240, 240, 240))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Highlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(51, 153, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Highlight, brush)
        self.progressbar.setPalette(palette)
        self.progressbar.setProperty("value", 0)
        self.progressbar.setTextVisible(True)
        self.progressbar.setObjectName(_fromUtf8("progressbar"))
        self.progress_label = QtGui.QLabel(DesireLines)
        self.progress_label.setGeometry(QtCore.QRect(270, 568, 301, 21))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label.setFont(font)
        self.progress_label.setObjectName(_fromUtf8("progress_label"))
        self.groupBox = QtGui.QGroupBox(DesireLines)
        self.groupBox.setGeometry(QtCore.QRect(10, 12, 621, 431))
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.but_load_new_matrix = QtGui.QPushButton(self.groupBox)
        self.but_load_new_matrix.setGeometry(QtCore.QRect(460, 400, 151, 23))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.but_load_new_matrix.setFont(font)
        self.but_load_new_matrix.setObjectName(_fromUtf8("but_load_new_matrix"))
        self.matrix_viewer = QtGui.QTableView(self.groupBox)
        self.matrix_viewer.setGeometry(QtCore.QRect(10, 20, 601, 371))
        self.matrix_viewer.setObjectName(_fromUtf8("matrix_viewer"))
        self.lbl_matrix_loaded = QtGui.QLabel(self.groupBox)
        self.lbl_matrix_loaded.setGeometry(QtCore.QRect(20, 400, 441, 21))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.lbl_matrix_loaded.setFont(font)
        self.lbl_matrix_loaded.setText(_fromUtf8(""))
        self.lbl_matrix_loaded.setWordWrap(False)
        self.lbl_matrix_loaded.setObjectName(_fromUtf8("lbl_matrix_loaded"))
        self.groupBox_2 = QtGui.QGroupBox(DesireLines)
        self.groupBox_2.setGeometry(QtCore.QRect(9, 446, 621, 111))
        self.groupBox_2.setTitle(_fromUtf8(""))
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.cancel = QtGui.QPushButton(self.groupBox_2)
        self.cancel.setGeometry(QtCore.QRect(470, 43, 140, 25))
        self.cancel.setObjectName(_fromUtf8("cancel"))
        self.create_dl = QtGui.QPushButton(self.groupBox_2)
        self.create_dl.setGeometry(QtCore.QRect(470, 10, 140, 25))
        self.create_dl.setObjectName(_fromUtf8("create_dl"))
        self.lblnodematch_13 = QtGui.QLabel(self.groupBox_2)
        self.lblnodematch_13.setGeometry(QtCore.QRect(9, 45, 121, 16))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.lblnodematch_13.setFont(font)
        self.lblnodematch_13.setObjectName(_fromUtf8("lblnodematch_13"))
        self.zoning_layer = QtGui.QComboBox(self.groupBox_2)
        self.zoning_layer.setGeometry(QtCore.QRect(130, 12, 321, 22))
        self.zoning_layer.setMaxVisibleItems(10)
        self.zoning_layer.setObjectName(_fromUtf8("zoning_layer"))
        self.radio_desire = QtGui.QRadioButton(self.groupBox_2)
        self.radio_desire.setGeometry(QtCore.QRect(10, 88, 81, 17))
        self.radio_desire.setCheckable(True)
        self.radio_desire.setChecked(False)
        self.radio_desire.setObjectName(_fromUtf8("radio_desire"))
        self.zone_id_field = QtGui.QComboBox(self.groupBox_2)
        self.zone_id_field.setGeometry(QtCore.QRect(129, 45, 321, 22))
        self.zone_id_field.setMaxVisibleItems(10)
        self.zone_id_field.setObjectName(_fromUtf8("zone_id_field"))
        self.lblnodematch_12 = QtGui.QLabel(self.groupBox_2)
        self.lblnodematch_12.setGeometry(QtCore.QRect(10, 12, 121, 16))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.lblnodematch_12.setFont(font)
        self.lblnodematch_12.setObjectName(_fromUtf8("lblnodematch_12"))
        self.radio_delaunay = QtGui.QRadioButton(self.groupBox_2)
        self.radio_delaunay.setGeometry(QtCore.QRect(110, 88, 101, 17))
        self.radio_delaunay.setCheckable(True)
        self.radio_delaunay.setChecked(True)
        self.radio_delaunay.setObjectName(_fromUtf8("radio_delaunay"))

        self.retranslateUi(DesireLines)
        QtCore.QMetaObject.connectSlotsByName(DesireLines)

    def retranslateUi(self, DesireLines):
        DesireLines.setWindowTitle(_translate("DesireLines", "Graph creation toolbox - Provided by www.xl-optim.com", None))
        self.lbl_funding2.setText(_translate("DesireLines", " www.ipea.gov.br", None))
        self.lbl_funding1.setText(_translate("DesireLines", "Partially funded by", None))
        self.progress_label.setText(_translate("DesireLines", "Status Message 0", None))
        self.groupBox.setTitle(_translate("DesireLines", "Demand Matrix", None))
        self.but_load_new_matrix.setText(_translate("DesireLines", "Load new matrix", None))
        self.cancel.setText(_translate("DesireLines", "Cancel", None))
        self.create_dl.setText(_translate("DesireLines", "Create Desire Lines", None))
        self.lblnodematch_13.setText(_translate("DesireLines", "ID Field", None))
        self.radio_desire.setText(_translate("DesireLines", "Desire Lines", None))
        self.lblnodematch_12.setText(_translate("DesireLines", "Zone or Node layer", None))
        self.radio_delaunay.setText(_translate("DesireLines", "Delaunay lines", None))

