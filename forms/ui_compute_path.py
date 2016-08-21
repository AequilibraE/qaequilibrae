# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_compute_path.ui'
#
# Created: Sat Aug 20 16:12:03 2016
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

class Ui_compute_path(object):
    def setupUi(self, compute_path):
        compute_path.setObjectName(_fromUtf8("compute_path"))
        compute_path.setWindowModality(QtCore.Qt.NonModal)
        compute_path.resize(627, 249)
        compute_path.setModal(False)
        self.groupBox = QtGui.QGroupBox(compute_path)
        self.groupBox.setGeometry(QtCore.QRect(20, 10, 591, 91))
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.load_graph_from_file = QtGui.QPushButton(self.groupBox)
        self.load_graph_from_file.setGeometry(QtCore.QRect(10, 20, 121, 23))
        self.load_graph_from_file.setObjectName(_fromUtf8("load_graph_from_file"))
        self.graph_file_name = QtGui.QLineEdit(self.groupBox)
        self.graph_file_name.setGeometry(QtCore.QRect(150, 20, 431, 20))
        self.graph_file_name.setObjectName(_fromUtf8("graph_file_name"))
        self.cb_minimizing = QtGui.QComboBox(self.groupBox)
        self.cb_minimizing.setGeometry(QtCore.QRect(150, 50, 121, 22))
        self.cb_minimizing.setObjectName(_fromUtf8("cb_minimizing"))
        self.progress_label_2 = QtGui.QLabel(self.groupBox)
        self.progress_label_2.setGeometry(QtCore.QRect(50, 52, 81, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label_2.setFont(font)
        self.progress_label_2.setObjectName(_fromUtf8("progress_label_2"))
        self.progress_label_3 = QtGui.QLabel(self.groupBox)
        self.progress_label_3.setGeometry(QtCore.QRect(290, 50, 81, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label_3.setFont(font)
        self.progress_label_3.setObjectName(_fromUtf8("progress_label_3"))
        self.all_centroids = QtGui.QLineEdit(self.groupBox)
        self.all_centroids.setGeometry(QtCore.QRect(350, 50, 51, 20))
        self.all_centroids.setObjectName(_fromUtf8("all_centroids"))
        self.block_paths = QtGui.QCheckBox(self.groupBox)
        self.block_paths.setGeometry(QtCore.QRect(420, 50, 161, 20))
        self.block_paths.setObjectName(_fromUtf8("block_paths"))
        self.do_dist_matrix = QtGui.QPushButton(compute_path)
        self.do_dist_matrix.setGeometry(QtCore.QRect(528, 219, 81, 23))
        self.do_dist_matrix.setObjectName(_fromUtf8("do_dist_matrix"))
        self.path_to = QtGui.QLineEdit(compute_path)
        self.path_to.setGeometry(QtCore.QRect(408, 219, 100, 20))
        self.path_to.setObjectName(_fromUtf8("path_to"))
        self.to_but = QtGui.QPushButton(compute_path)
        self.to_but.setGeometry(QtCore.QRect(368, 217, 35, 23))
        self.to_but.setObjectName(_fromUtf8("to_but"))
        self.groupBox_2 = QtGui.QGroupBox(compute_path)
        self.groupBox_2.setGeometry(QtCore.QRect(20, 161, 591, 51))
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.cb_node_layer = QtGui.QComboBox(self.groupBox_2)
        self.cb_node_layer.setGeometry(QtCore.QRect(50, 20, 221, 22))
        self.cb_node_layer.setObjectName(_fromUtf8("cb_node_layer"))
        self.cb_data_field = QtGui.QComboBox(self.groupBox_2)
        self.cb_data_field.setGeometry(QtCore.QRect(360, 20, 221, 22))
        self.cb_data_field.setObjectName(_fromUtf8("cb_data_field"))
        self.progress_label_4 = QtGui.QLabel(self.groupBox_2)
        self.progress_label_4.setGeometry(QtCore.QRect(10, 20, 81, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label_4.setFont(font)
        self.progress_label_4.setObjectName(_fromUtf8("progress_label_4"))
        self.progress_label_5 = QtGui.QLabel(self.groupBox_2)
        self.progress_label_5.setGeometry(QtCore.QRect(310, 20, 51, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label_5.setFont(font)
        self.progress_label_5.setObjectName(_fromUtf8("progress_label_5"))
        self.path_from = QtGui.QLineEdit(compute_path)
        self.path_from.setGeometry(QtCore.QRect(248, 219, 100, 20))
        self.path_from.setObjectName(_fromUtf8("path_from"))
        self.from_but = QtGui.QPushButton(compute_path)
        self.from_but.setGeometry(QtCore.QRect(210, 217, 35, 23))
        self.from_but.setObjectName(_fromUtf8("from_but"))
        self.groupBox_3 = QtGui.QGroupBox(compute_path)
        self.groupBox_3.setGeometry(QtCore.QRect(20, 105, 591, 51))
        self.groupBox_3.setObjectName(_fromUtf8("groupBox_3"))
        self.cb_link_layer = QtGui.QComboBox(self.groupBox_3)
        self.cb_link_layer.setGeometry(QtCore.QRect(50, 20, 221, 22))
        self.cb_link_layer.setObjectName(_fromUtf8("cb_link_layer"))
        self.cb_link_id_field = QtGui.QComboBox(self.groupBox_3)
        self.cb_link_id_field.setGeometry(QtCore.QRect(360, 20, 221, 22))
        self.cb_link_id_field.setObjectName(_fromUtf8("cb_link_id_field"))
        self.progress_label_6 = QtGui.QLabel(self.groupBox_3)
        self.progress_label_6.setGeometry(QtCore.QRect(10, 20, 81, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label_6.setFont(font)
        self.progress_label_6.setObjectName(_fromUtf8("progress_label_6"))
        self.progress_label_7 = QtGui.QLabel(self.groupBox_3)
        self.progress_label_7.setGeometry(QtCore.QRect(317, 20, 51, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label_7.setFont(font)
        self.progress_label_7.setObjectName(_fromUtf8("progress_label_7"))

        self.retranslateUi(compute_path)
        QtCore.QMetaObject.connectSlotsByName(compute_path)

    def retranslateUi(self, compute_path):
        compute_path.setWindowTitle(_translate("compute_path", "Single shortest path toolbox                                    {Created by www.xl-optim.com}", None))
        self.groupBox.setTitle(_translate("compute_path", "GRAPH", None))
        self.load_graph_from_file.setText(_translate("compute_path", "Load Graph file", None))
        self.progress_label_2.setText(_translate("compute_path", "Minimize field:", None))
        self.progress_label_3.setText(_translate("compute_path", "Centroids:", None))
        self.block_paths.setText(_translate("compute_path", "Block path through centroids", None))
        self.do_dist_matrix.setText(_translate("compute_path", "Compute", None))
        self.to_but.setText(_translate("compute_path", "To", None))
        self.groupBox_2.setTitle(_translate("compute_path", "Node Layer", None))
        self.progress_label_4.setText(_translate("compute_path", "Layer", None))
        self.progress_label_5.setText(_translate("compute_path", "Node ID", None))
        self.from_but.setText(_translate("compute_path", "From", None))
        self.groupBox_3.setTitle(_translate("compute_path", "Link Layer", None))
        self.progress_label_6.setText(_translate("compute_path", "Layer", None))
        self.progress_label_7.setText(_translate("compute_path", "Link ID", None))

