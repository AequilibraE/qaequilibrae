# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui_link_query_builder.ui'
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

class Ui_link_query_builder(object):
    def setupUi(self, link_query_builder):
        link_query_builder.setObjectName(_fromUtf8("link_query_builder"))
        link_query_builder.setEnabled(True)
        link_query_builder.resize(471, 324)
        self.selected_links = QtGui.QTableWidget(link_query_builder)
        self.selected_links.setGeometry(QtCore.QRect(250, 50, 211, 231))
        self.selected_links.setObjectName(_fromUtf8("selected_links"))
        self.selected_links.setColumnCount(3)
        self.selected_links.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.selected_links.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.selected_links.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        self.selected_links.setHorizontalHeaderItem(2, item)
        self.filter_field = QtGui.QLineEdit(link_query_builder)
        self.filter_field.setGeometry(QtCore.QRect(99, 16, 131, 26))
        self.filter_field.setObjectName(_fromUtf8("filter_field"))
        self.txt_query_name = QtGui.QLineEdit(link_query_builder)
        self.txt_query_name.setGeometry(QtCore.QRect(100, 290, 151, 26))
        self.txt_query_name.setObjectName(_fromUtf8("txt_query_name"))
        self.label = QtGui.QLabel(link_query_builder)
        self.label.setGeometry(QtCore.QRect(12, 294, 81, 16))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label.setFont(font)
        self.label.setObjectName(_fromUtf8("label"))
        self.but_build_query = QtGui.QPushButton(link_query_builder)
        self.but_build_query.setEnabled(False)
        self.but_build_query.setGeometry(QtCore.QRect(290, 290, 171, 26))
        self.but_build_query.setObjectName(_fromUtf8("but_build_query"))
        self.label_2 = QtGui.QLabel(link_query_builder)
        self.label_2.setGeometry(QtCore.QRect(14, 20, 71, 16))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.label_2.setFont(font)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.radio_and = QtGui.QRadioButton(link_query_builder)
        self.radio_and.setGeometry(QtCore.QRect(280, 20, 51, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.radio_and.setFont(font)
        self.radio_and.setChecked(True)
        self.radio_and.setObjectName(_fromUtf8("radio_and"))
        self.radio_or = QtGui.QRadioButton(link_query_builder)
        self.radio_or.setGeometry(QtCore.QRect(370, 20, 51, 17))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.radio_or.setFont(font)
        self.radio_or.setObjectName(_fromUtf8("radio_or"))
        self.graph_links_list = QtGui.QTableView(link_query_builder)
        self.graph_links_list.setGeometry(QtCore.QRect(10, 50, 201, 231))
        self.graph_links_list.setObjectName(_fromUtf8("graph_links_list"))
        self.but_add_to_list = QtGui.QToolButton(link_query_builder)
        self.but_add_to_list.setGeometry(QtCore.QRect(218, 100, 25, 131))
        self.but_add_to_list.setObjectName(_fromUtf8("but_add_to_list"))

        self.retranslateUi(link_query_builder)
        QtCore.QMetaObject.connectSlotsByName(link_query_builder)

    def retranslateUi(self, link_query_builder):
        link_query_builder.setWindowTitle(_translate("link_query_builder", "Critical link query builder", None))
        item = self.selected_links.horizontalHeaderItem(0)
        item.setText(_translate("link_query_builder", "Link ID", None))
        item = self.selected_links.horizontalHeaderItem(1)
        item.setText(_translate("link_query_builder", "Dir", None))
        item = self.selected_links.horizontalHeaderItem(2)
        item.setText(_translate("link_query_builder", "Del", None))
        self.label.setText(_translate("link_query_builder", "Query name", None))
        self.but_build_query.setText(_translate("link_query_builder", "Accept", None))
        self.label_2.setText(_translate("link_query_builder", "Filter link", None))
        self.radio_and.setText(_translate("link_query_builder", "And", None))
        self.radio_or.setText(_translate("link_query_builder", "Or", None))
        self.but_add_to_list.setText(_translate("link_query_builder", ">", None))

