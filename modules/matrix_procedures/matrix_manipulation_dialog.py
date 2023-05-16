import logging
import os
from functools import partial

from ..common_tools import standard_path
from qgis.PyQt import uic
from qgis.PyQt.Qsci import QsciLexerPython
from qgis.PyQt.QtGui import QFont
from qgis.PyQt.QtWidgets import QDialog
from qgis.core import QGridLayout, QWidget, QTableView, QHBoxLayout, QCheckBox, QSpacerItem, QSizePolicy
from qgis.core import QLabel, QSpinBox, QComboBox
from aequilibrae.aequilibrae.matrix import AequilibraeMatrix
from ..common_tools import NumpyModel, GetOutputFileName

FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "forms/ui_matrix_viewer.ui"))


class MatrixManipulationDialog(QDialog, FORM_CLASS):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        self.path = standard_path()
        self.error = None
        self.matrices = {}
        self.logger = logging.getLogger("AequilibraEGUI")

        self.but_load.clicked.connect(self.find_new_matrix)

        # MATH tab
        # Setting the advanced mode
        font = QFont()
        font.setFamily("Courier")
        font.setFixedPitch(True)
        font.setPointSize(12)
        lexer = QsciLexerPython()
        lexer.setDefaultFont(font)
        self.expression_box.setLexer(lexer)

        # toggling between modes
        self.rdo_basic_math.toggled.connect(self.toggle_basic_and_advanced)
        self.rdo_advanced_math.toggled.connect(self.toggle_basic_and_advanced)
        self.toggle_basic_and_advanced()

    def load_new_matrix(self, dataset):
        config = {}

        mat_name = self.find_non_conflicting_name(dataset.name, self.matrices)
        config["dataset"] = dataset

        contents = QWidget(self.matrix_tabs)
        new_tab_layout = QGridLayout()
        new_table_view = QTableView()
        new_tab_layout.addWidget(new_table_view)
        config["table"] = new_table_view

        # Settings for displaying
        show_layout = QHBoxLayout()

        # Thousand separator
        separator = QCheckBox()
        separator.setChecked(True)
        separator.setText("Thousands separator")
        separator.toggled.connect(partial(self.format_showing, mat_name))
        show_layout.addWidget(separator)
        config["separator"] = separator

        self.spacer = QSpacerItem(5, 0, QSizePolicy.Expanding, QSizePolicy.Minimum)
        show_layout.addItem(self.spacer)

        # Decimals
        txt = QLabel()
        txt.setText("Decimal places")
        show_layout.addWidget(txt)
        decimals = QSpinBox()
        decimals.valueChanged.connect(partial(self.format_showing, mat_name))
        decimals.setMinimum(0)
        decimals.setValue(4)
        decimals.setMaximum(10)
        config["decimals"] = decimals

        show_layout.addWidget(decimals)
        new_tab_layout.addItem(show_layout)

        dataset.computational_view([dataset.names[0]])
        # Matrices need cores and indices to be set as well
        mat_layout = QHBoxLayout()
        mat_list = QComboBox()
        for n in dataset.names:
            mat_list.addItem(n)

        mat_list.currentIndexChanged.connect(partial(self.change_matrix_cores, mat_name))
        mat_layout.addWidget(mat_list)
        config["mat_list"] = mat_list

        idx_list = QComboBox()
        for i in dataset.index_names:
            idx_list.addItem(i)
        idx_list.currentIndexChanged.connect(partial(self.change_matrix_cores, mat_name))
        mat_layout.addWidget(idx_list)
        new_tab_layout.addItem(mat_layout)
        config["idx_list"] = idx_list

        self.matrices[mat_name] = config

        contents.setLayout(new_tab_layout)
        self.matrix_tabs.addTab(contents, mat_name)

        self.change_matrix_cores(mat_name)

    def find_new_matrix(self):
        data_path, _ = GetOutputFileName(self, "AequilibraE matrix", ["Aequilibrae matrix(*.aem)"], ".aem", self.path)

        if data_path is not None:
            dataset = AequilibraeMatrix()

            try:
                dataset.load(data_path)
                self.load_new_matrix(dataset)
            except Exception as e:
                self.logger.error(e.args)
                self.error = "Could not load matrix"

    def find_non_conflicting_name(self, data_name, dictio):
        if len(data_name) < 1:
            data_name = "Matrix"

        if data_name in dictio.keys():
            i = 1
            new_data_name = data_name + "_" + str(i)
            while new_data_name in dictio.keys():
                i += 1
                new_data_name = data_name + "_" + str(i)
            data_name = new_data_name
        return data_name

    def format_showing(self, mat_name):
        if mat_name in self.matrices.keys():
            decimals = self.matrices[mat_name]["decimals"]
            new_table_view = self.matrices[mat_name]["table"]
            data_to_show = self.matrices[mat_name]["dataset"]

            dec = decimals.value()
            separator = self.matrices[mat_name]["separator"].isChecked()
            m = NumpyModel(data_to_show, separator, dec)
            new_table_view.clearSpans()
            new_table_view.setModel(m)

    def change_matrix_cores(self, mat_name):
        if mat_name in self.matrices.keys():
            mat_list = self.matrices[mat_name]["mat_list"]
            data_to_show = self.matrices[mat_name]["dataset"]
            data_to_show.computational_view([mat_list.currentText()])
            data_to_show.set_index(0)
            self.format_showing(mat_name)

    def toggle_basic_and_advanced(self):
        bsc = self.rdo_basic_math.isChecked()
        adv = self.rdo_advanced_math.isChecked()

        self.frame_math_advanced.setVisible(adv)
        self.frame_math_simple_1.setVisible(bsc)
        self.frame_math_simple_2.setVisible(bsc)

    def export(self):
        new_name, file_type = GetOutputFileName(
            self, self.data_type, ["Comma-separated file(*.csv)"], ".csv", self.path
        )
        if new_name is not None:
            self.data_to_show.export(new_name)

    def exit_procedure(self):
        self.close()
