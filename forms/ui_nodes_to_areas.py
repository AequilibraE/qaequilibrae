# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_nodes_to_areas.ui'
#
# Created: Tue Jul 29 17:28:43 2014
#      by: PyQt4 UI code generator 4.10.4
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

class Ui_nodes_to_area(object):
    def setupUi(self, nodes_to_area):
        nodes_to_area.setObjectName(_fromUtf8("nodes_to_area"))
        nodes_to_area.resize(400, 478)
        font = QtGui.QFont()
        font.setPointSize(9)
        nodes_to_area.setFont(font)
        self.buttonBox = QtGui.QDialogButtonBox(nodes_to_area)
        self.buttonBox.setGeometry(QtCore.QRect(40, 440, 341, 32))
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.groupBox = QtGui.QGroupBox(nodes_to_area)
        self.groupBox.setGeometry(QtCore.QRect(10, 10, 381, 101))
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.nodefield = QtGui.QComboBox(self.groupBox)
        self.nodefield.setGeometry(QtCore.QRect(160, 60, 211, 22))
        self.nodefield.setObjectName(_fromUtf8("nodefield"))
        self.nodelayer = QtGui.QComboBox(self.groupBox)
        self.nodelayer.setGeometry(QtCore.QRect(160, 30, 211, 22))
        self.nodelayer.setObjectName(_fromUtf8("nodelayer"))
        self.label_2 = QtGui.QLabel(self.groupBox)
        self.label_2.setGeometry(QtCore.QRect(10, 60, 121, 16))
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setGeometry(QtCore.QRect(10, 30, 121, 16))
        self.label.setObjectName(_fromUtf8("label"))
        self.groupBox_2 = QtGui.QGroupBox(nodes_to_area)
        self.groupBox_2.setGeometry(QtCore.QRect(10, 120, 381, 101))
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.areafield = QtGui.QComboBox(self.groupBox_2)
        self.areafield.setGeometry(QtCore.QRect(160, 60, 211, 22))
        self.areafield.setObjectName(_fromUtf8("areafield"))
        self.arealayer = QtGui.QComboBox(self.groupBox_2)
        self.arealayer.setGeometry(QtCore.QRect(160, 30, 211, 22))
        self.arealayer.setObjectName(_fromUtf8("arealayer"))
        self.label_5 = QtGui.QLabel(self.groupBox_2)
        self.label_5.setGeometry(QtCore.QRect(10, 60, 121, 16))
        self.label_5.setObjectName(_fromUtf8("label_5"))
        self.label_6 = QtGui.QLabel(self.groupBox_2)
        self.label_6.setGeometry(QtCore.QRect(10, 30, 121, 16))
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.groupBox_3 = QtGui.QGroupBox(nodes_to_area)
        self.groupBox_3.setGeometry(QtCore.QRect(10, 230, 381, 111))
        self.groupBox_3.setObjectName(_fromUtf8("groupBox_3"))
        self.areamatching = QtGui.QComboBox(self.groupBox_3)
        self.areamatching.setEnabled(True)
        self.areamatching.setGeometry(QtCore.QRect(160, 80, 211, 22))
        self.areamatching.setMaxVisibleItems(10)
        self.areamatching.setObjectName(_fromUtf8("areamatching"))
        self.nodematching = QtGui.QComboBox(self.groupBox_3)
        self.nodematching.setGeometry(QtCore.QRect(160, 50, 211, 22))
        self.nodematching.setMaxVisibleItems(10)
        self.nodematching.setObjectName(_fromUtf8("nodematching"))
        self.lblareamatch = QtGui.QLabel(self.groupBox_3)
        self.lblareamatch.setGeometry(QtCore.QRect(10, 80, 121, 16))
        self.lblareamatch.setObjectName(_fromUtf8("lblareamatch"))
        self.lblnodematch = QtGui.QLabel(self.groupBox_3)
        self.lblnodematch.setGeometry(QtCore.QRect(10, 50, 121, 16))
        self.lblnodematch.setObjectName(_fromUtf8("lblnodematch"))
        self.needsmatching = QtGui.QCheckBox(self.groupBox_3)
        self.needsmatching.setGeometry(QtCore.QRect(10, 20, 221, 17))
        self.needsmatching.setChecked(False)
        self.needsmatching.setObjectName(_fromUtf8("needsmatching"))
        self.groupBox_4 = QtGui.QGroupBox(nodes_to_area)
        self.groupBox_4.setGeometry(QtCore.QRect(10, 350, 381, 81))
        self.groupBox_4.setObjectName(_fromUtf8("groupBox_4"))
        self.sum = QtGui.QRadioButton(self.groupBox_4)
        self.sum.setGeometry(QtCore.QRect(10, 20, 51, 17))
        self.sum.setChecked(True)
        self.sum.setObjectName(_fromUtf8("sum"))
        self.max = QtGui.QRadioButton(self.groupBox_4)
        self.max.setGeometry(QtCore.QRect(70, 20, 51, 17))
        self.max.setObjectName(_fromUtf8("max"))
        self.min = QtGui.QRadioButton(self.groupBox_4)
        self.min.setGeometry(QtCore.QRect(130, 20, 51, 17))
        self.min.setObjectName(_fromUtf8("min"))
        self.avg = QtGui.QRadioButton(self.groupBox_4)
        self.avg.setGeometry(QtCore.QRect(190, 20, 71, 17))
        self.avg.setObjectName(_fromUtf8("avg"))
        self.divide_value = QtGui.QCheckBox(self.groupBox_4)
        self.divide_value.setGeometry(QtCore.QRect(10, 50, 321, 17))
        self.divide_value.setObjectName(_fromUtf8("divide_value"))
        self.progressBar = QtGui.QProgressBar(nodes_to_area)
        self.progressBar.setGeometry(QtCore.QRect(10, 440, 118, 23))
        self.progressBar.setProperty("value", 0)
        self.progressBar.setObjectName(_fromUtf8("progressBar"))

        self.retranslateUi(nodes_to_area)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), nodes_to_area.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), nodes_to_area.reject)
        QtCore.QMetaObject.connectSlotsByName(nodes_to_area)

    def retranslateUi(self, nodes_to_area):
        nodes_to_area.setWindowTitle(_translate("nodes_to_area", "AequilibraE  -  Node to Area data aggregation", None))
        self.groupBox.setTitle(_translate("nodes_to_area", "Data source", None))
        self.label_2.setText(_translate("nodes_to_area", "Node field", None))
        self.label.setText(_translate("nodes_to_area", "Node Layer", None))
        self.groupBox_2.setTitle(_translate("nodes_to_area", "Data destination", None))
        self.label_5.setText(_translate("nodes_to_area", "Area field", None))
        self.label_6.setText(_translate("nodes_to_area", "Area Layer", None))
        self.groupBox_3.setTitle(_translate("nodes_to_area", "Aggregation criteria", None))
        self.lblareamatch.setText(_translate("nodes_to_area", "Area field", None))
        self.lblnodematch.setText(_translate("nodes_to_area", "Node field", None))
        self.needsmatching.setText(_translate("nodes_to_area", "Fields need to have matching values", None))
        self.groupBox_4.setTitle(_translate("nodes_to_area", "Operation", None))
        self.sum.setText(_translate("nodes_to_area", "Sum", None))
        self.max.setText(_translate("nodes_to_area", "Max", None))
        self.min.setText(_translate("nodes_to_area", "Min", None))
        self.avg.setText(_translate("nodes_to_area", "Average", None))
        self.divide_value.setText(_translate("nodes_to_area", "Divided value in case of multiple area overlapping", None))

