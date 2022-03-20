# Filtering largely adapted from http://stackoverflow.com/questions/34252413/how-to-create-a-filter-for-qtablewidget
import os

import numpy as np

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import QSortFilterProxyModel
from qgis.PyQt.QtWidgets import QPushButton, QAbstractItemView, QTableWidgetItem
from ..common_tools import LinkQueryModel

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_link_query_builder.ui"))


class LoadSelectLinkQueryBuilderDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, iface, graph, window_title):
        QtWidgets.QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.graph = graph

        self.setWindowTitle(window_title)

        self.links = []
        self.label = None
        self.operation = None
        self.tot_links = 0
        self.query_name = None
        self.query_type = "or"
        self.links = None

        dt = [("link_id", np.int32), ("direction", "|S2")]

        self.data = np.zeros(graph.shape[0], dtype=dt)

        self.data["link_id"][:] = graph["link_id"][:]

        self.data["direction"][graph["direction"] < 0] = "BA"
        self.data["direction"][graph["direction"] > 0] = "AB"

        self.data.sort(order="link_id")

        self.model = LinkQueryModel(self.data, ["Link ID", "Dir"])

        # filter proxy model
        filter_proxy_model = QSortFilterProxyModel()
        filter_proxy_model.setSourceModel(self.model)
        filter_proxy_model.setFilterKeyColumn(0)  # third column

        # line edit for filtering
        self.filter_field.textChanged.connect(filter_proxy_model.setFilterRegExp)
        self.graph_links_list.setModel(filter_proxy_model)
        self.graph_links_list.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.graph_links_list.setColumnWidth(0, 80)
        self.graph_links_list.setColumnWidth(1, 60)

        self.selected_links.setColumnWidth(0, 70)
        self.selected_links.setColumnWidth(1, 55)
        self.selected_links.setColumnWidth(2, 40)

        self.txt_query_name.textChanged.connect(self.check_preparedness)
        self.but_add_to_list.clicked.connect(self.add_link_to_query)
        self.but_build_query.clicked.connect(self.save_query)

    def add_link_to_query(self):
        selection = self.graph_links_list.selectedIndexes()
        if selection:
            rows = sorted(index.row() for index in selection)
            columns = sorted(index.column() for index in selection)
            rowcount = rows[-1] - rows[0] + 1
            colcount = columns[-1] - columns[0] + 1
            table = [[""] * colcount for _ in range(rowcount)]
            for index in selection:
                row = index.row() - rows[0]
                column = index.column() - columns[0]
                table[row][column] = str(index.data())

            for i in table:
                if len(i[0]):
                    self.selected_links.setRowCount(self.tot_links + 1)
                    link_id = i[0]
                    self.selected_links.setItem(self.tot_links, 0, QTableWidgetItem(link_id))

                    direc = i[1]
                    self.selected_links.setItem(self.tot_links, 1, QTableWidgetItem(direc))

                    del_button = QPushButton("X")
                    del_button.clicked.connect(self.click_button_inside_the_list)
                    self.selected_links.setCellWidget(self.tot_links, 2, del_button)
                    self.tot_links += 1
        self.check_preparedness()

    def click_button_inside_the_list(self):
        button = self.sender()
        index = self.selected_links.indexAt(button.pos())
        row = index.row()
        self.selected_links.removeRow(row)
        self.tot_links -= 1

    def check_preparedness(self):
        self.query_name = self.txt_query_name.text()
        self.but_build_query.setEnabled(False)
        if self.tot_links:
            if len(self.query_name):
                self.but_build_query.setEnabled(True)

    def save_query(self):
        self.links = []
        for i in range(self.tot_links):
            link_id = self.selected_links.item(i, 0).text()
            direc = self.selected_links.item(i, 1).text()
            self.links.append((link_id, direc))

        if self.radio_and.isChecked():
            self.query_type = "and"

        self.exit_procedure()

    def exit_procedure(self):
        self.close()
