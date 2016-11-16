# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_matrix_viewer.ui'
#
# Created: Mon May 04 16:32:15 2015
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

class Ui_MatrixViewer(object):
    def setupUi(self, MatrixViewer):
        MatrixViewer.setObjectName(_fromUtf8("MatrixViewer"))
        MatrixViewer.setWindowModality(QtCore.Qt.WindowModal)
        MatrixViewer.resize(817, 598)
        self.centralwidget = QtGui.QWidget(MatrixViewer)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.matrix_cores_selector = QtGui.QComboBox(self.centralwidget)
        self.matrix_cores_selector.setGeometry(QtCore.QRect(10, 30, 321, 22))
        self.matrix_cores_selector.setObjectName(_fromUtf8("matrix_cores_selector"))
        self.groupBox = QtGui.QGroupBox(self.centralwidget)
        self.groupBox.setGeometry(QtCore.QRect(350, 10, 451, 51))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.groupBox.setFont(font)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.layoutWidget = QtGui.QWidget(self.groupBox)
        self.layoutWidget.setGeometry(QtCore.QRect(20, 20, 210, 22))
        self.layoutWidget.setObjectName(_fromUtf8("layoutWidget"))
        self.horizontalLayout = QtGui.QHBoxLayout(self.layoutWidget)
        self.horizontalLayout.setMargin(0)
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.marg_no_marg = QtGui.QRadioButton(self.layoutWidget)
        self.marg_no_marg.setChecked(True)
        self.marg_no_marg.setObjectName(_fromUtf8("marg_no_marg"))
        self.horizontalLayout.addWidget(self.marg_no_marg)
        self.marg_sum_marg = QtGui.QRadioButton(self.layoutWidget)
        self.marg_sum_marg.setObjectName(_fromUtf8("marg_sum_marg"))
        self.horizontalLayout.addWidget(self.marg_sum_marg)
        self.marg_max_marg = QtGui.QRadioButton(self.layoutWidget)
        self.marg_max_marg.setObjectName(_fromUtf8("marg_max_marg"))
        self.horizontalLayout.addWidget(self.marg_max_marg)
        self.marg_min_marg = QtGui.QRadioButton(self.layoutWidget)
        self.marg_min_marg.setObjectName(_fromUtf8("marg_min_marg"))
        self.horizontalLayout.addWidget(self.marg_min_marg)
        self.label = QtGui.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(10, 10, 71, 16))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setObjectName(_fromUtf8("label"))
        self.matrix_pile = QtGui.QTabWidget(self.centralwidget)
        self.matrix_pile.setGeometry(QtCore.QRect(10, 70, 791, 451))
        self.matrix_pile.setObjectName(_fromUtf8("matrix_pile"))
        self.tab_3 = QtGui.QWidget()
        self.tab_3.setObjectName(_fromUtf8("tab_3"))
        self.but_close = QtGui.QPushButton(self.tab_3)
        self.but_close.setGeometry(QtCore.QRect(630, 390, 131, 23))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.but_close.setFont(font)
        self.but_close.setObjectName(_fromUtf8("but_close"))
        self.but_load_new_matrix = QtGui.QPushButton(self.tab_3)
        self.but_load_new_matrix.setGeometry(QtCore.QRect(480, 390, 131, 23))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.but_load_new_matrix.setFont(font)
        self.but_load_new_matrix.setObjectName(_fromUtf8("but_load_new_matrix"))
        self.radioButton = QtGui.QRadioButton(self.tab_3)
        self.radioButton.setGeometry(QtCore.QRect(20, 10, 82, 17))
        self.radioButton.setObjectName(_fromUtf8("radioButton"))
        self.radioButton_2 = QtGui.QRadioButton(self.tab_3)
        self.radioButton_2.setGeometry(QtCore.QRect(520, 10, 82, 17))
        self.radioButton_2.setObjectName(_fromUtf8("radioButton_2"))
        self.radioButton_3 = QtGui.QRadioButton(self.tab_3)
        self.radioButton_3.setGeometry(QtCore.QRect(650, 10, 82, 17))
        self.radioButton_3.setObjectName(_fromUtf8("radioButton_3"))
        self.matrix_pile.addTab(self.tab_3, _fromUtf8(""))
        
        self.retranslateUi(MatrixViewer)
        self.matrix_pile.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MatrixViewer)

    def retranslateUi(self, MatrixViewer):
        MatrixViewer.setWindowTitle(_translate("MatrixViewer", "MainWindow", None))
        self.groupBox.setTitle(_translate("MatrixViewer", "Marginals", None))
        self.marg_no_marg.setText(_translate("MatrixViewer", "None", None))
        self.marg_sum_marg.setText(_translate("MatrixViewer", "Sum", None))
        self.marg_max_marg.setText(_translate("MatrixViewer", "Max", None))
        self.marg_min_marg.setText(_translate("MatrixViewer", "Min", None))
        self.label.setText(_translate("MatrixViewer", "Matrix cores", None))
        self.but_close.setText(_translate("MatrixViewer", "Close", None))
        self.but_load_new_matrix.setText(_translate("MatrixViewer", "Load new matrix", None))
        self.radioButton.setText(_translate("MatrixViewer", "CSV Matrix", None))
        self.radioButton_2.setText(_translate("MatrixViewer", "Numpy Array", None))
        self.radioButton_3.setText(_translate("MatrixViewer", "OMX/HDF5", None))
        self.matrix_pile.setTabText(self.matrix_pile.indexOf(self.tab_3), _translate("MatrixViewer", "Loading Matrices", None))

