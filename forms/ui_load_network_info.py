# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_load_network_info.ui'
#
# Created: Mon Sep 05 04:21:54 2016
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

class Ui_load_network_info(object):
    def setupUi(self, load_network_info):
        load_network_info.setObjectName(_fromUtf8("load_network_info"))
        load_network_info.setWindowModality(QtCore.Qt.NonModal)
        load_network_info.resize(613, 203)
        load_network_info.setModal(False)
        self.do_load_graph = QtGui.QPushButton(load_network_info)
        self.do_load_graph.setGeometry(QtCore.QRect(22, 170, 571, 23))
        self.do_load_graph.setObjectName(_fromUtf8("do_load_graph"))
        self.cb_data_field = QtGui.QComboBox(load_network_info)
        self.cb_data_field.setGeometry(QtCore.QRect(372, 130, 221, 22))
        self.cb_data_field.setObjectName(_fromUtf8("cb_data_field"))
        self.progress_label_5 = QtGui.QLabel(load_network_info)
        self.progress_label_5.setGeometry(QtCore.QRect(322, 130, 51, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label_5.setFont(font)
        self.progress_label_5.setObjectName(_fromUtf8("progress_label_5"))
        self.progress_label_4 = QtGui.QLabel(load_network_info)
        self.progress_label_4.setGeometry(QtCore.QRect(22, 130, 81, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label_4.setFont(font)
        self.progress_label_4.setObjectName(_fromUtf8("progress_label_4"))
        self.cb_node_layer = QtGui.QComboBox(load_network_info)
        self.cb_node_layer.setGeometry(QtCore.QRect(92, 130, 211, 22))
        self.cb_node_layer.setObjectName(_fromUtf8("cb_node_layer"))
        self.cb_link_id_field = QtGui.QComboBox(load_network_info)
        self.cb_link_id_field.setGeometry(QtCore.QRect(372, 90, 221, 22))
        self.cb_link_id_field.setObjectName(_fromUtf8("cb_link_id_field"))
        self.cb_link_layer = QtGui.QComboBox(load_network_info)
        self.cb_link_layer.setGeometry(QtCore.QRect(92, 90, 211, 22))
        self.cb_link_layer.setObjectName(_fromUtf8("cb_link_layer"))
        self.progress_label_6 = QtGui.QLabel(load_network_info)
        self.progress_label_6.setGeometry(QtCore.QRect(22, 90, 71, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label_6.setFont(font)
        self.progress_label_6.setObjectName(_fromUtf8("progress_label_6"))
        self.progress_label_7 = QtGui.QLabel(load_network_info)
        self.progress_label_7.setGeometry(QtCore.QRect(322, 90, 51, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label_7.setFont(font)
        self.progress_label_7.setObjectName(_fromUtf8("progress_label_7"))
        self.block_paths = QtGui.QCheckBox(load_network_info)
        self.block_paths.setGeometry(QtCore.QRect(420, 50, 171, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(True)
        font.setItalic(True)
        font.setWeight(75)
        self.block_paths.setFont(font)
        self.block_paths.setObjectName(_fromUtf8("block_paths"))
        self.progress_label_2 = QtGui.QLabel(load_network_info)
        self.progress_label_2.setGeometry(QtCore.QRect(60, 52, 81, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label_2.setFont(font)
        self.progress_label_2.setObjectName(_fromUtf8("progress_label_2"))
        self.cb_minimizing = QtGui.QComboBox(load_network_info)
        self.cb_minimizing.setGeometry(QtCore.QRect(160, 50, 121, 22))
        self.cb_minimizing.setObjectName(_fromUtf8("cb_minimizing"))
        self.all_centroids = QtGui.QLineEdit(load_network_info)
        self.all_centroids.setGeometry(QtCore.QRect(360, 50, 51, 20))
        self.all_centroids.setObjectName(_fromUtf8("all_centroids"))
        self.load_graph_from_file = QtGui.QPushButton(load_network_info)
        self.load_graph_from_file.setGeometry(QtCore.QRect(20, 20, 121, 23))
        self.load_graph_from_file.setObjectName(_fromUtf8("load_graph_from_file"))
        self.graph_file_name = QtGui.QLineEdit(load_network_info)
        self.graph_file_name.setGeometry(QtCore.QRect(160, 20, 431, 20))
        self.graph_file_name.setObjectName(_fromUtf8("graph_file_name"))
        self.progress_label_3 = QtGui.QLabel(load_network_info)
        self.progress_label_3.setGeometry(QtCore.QRect(300, 50, 81, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        self.progress_label_3.setFont(font)
        self.progress_label_3.setObjectName(_fromUtf8("progress_label_3"))

        self.retranslateUi(load_network_info)
        QtCore.QMetaObject.connectSlotsByName(load_network_info)

    def retranslateUi(self, load_network_info):
        load_network_info.setWindowTitle(_translate("load_network_info", "Graph and Network setting toolbox                                    {By www.xl-optim.com}", None))
        self.do_load_graph.setText(_translate("load_network_info", "Done!", None))
        self.progress_label_5.setText(_translate("load_network_info", "Node ID", None))
        self.progress_label_4.setText(_translate("load_network_info", "Node Layer", None))
        self.progress_label_6.setText(_translate("load_network_info", "Line Layer", None))
        self.progress_label_7.setText(_translate("load_network_info", "Link ID", None))
        self.block_paths.setText(_translate("load_network_info", "No paths through centroids", None))
        self.progress_label_2.setText(_translate("load_network_info", "Minimize field:", None))
        self.load_graph_from_file.setText(_translate("load_network_info", "Load Graph file", None))
        self.progress_label_3.setText(_translate("load_network_info", "Centroids:", None))

