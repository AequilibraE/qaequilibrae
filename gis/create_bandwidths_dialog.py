"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Main interface for creating stacked bandwidths for link layers
 Purpose:    Load GUI and user interface for the bandwidth creation

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-10-24
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import qgis
from qgis.core import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.gui import QgsMapLayerProxyModel

from auxiliary_functions import *
import sys
import os
from global_parameters import *
from random import randint

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/forms/")

from ui_bandwidths import Ui_bandwidths
from auxiliary_functions import get_parameter_chain


class CreateBandwidthsDialog(QDialog, Ui_bandwidths):
    def __init__(self, iface):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        
        self.tot_bands = 0
        self.band_size = 1.0
        self.space_size = 0.01
        self.layer = None
        self.drive_side = get_parameter_chain(['system', 'driving side'])

        # layers and fields        # For adding skims
        self.mMapLayerComboBox.setFilters(QgsMapLayerProxyModel.LineLayer)
        self.mMapLayerComboBox.layerChanged.connect(self.add_fields_to_cboxes)

        # space slider
        self.slider_spacer.setMinimum(1)
        self.slider_spacer.setMaximum(100)
        self.slider_spacer.setValue(1)
        self.slider_spacer.setTickPosition(QSlider.TicksBelow)
        self.slider_spacer.setTickInterval(5)
        self.slider_spacer.valueChanged.connect(self.spacevaluechange)

        # band slider
        self.slider_band_size.setMinimum(5)
        self.slider_band_size.setMaximum(150)
        self.slider_band_size.setValue(1)
        self.slider_band_size.setTickPosition(QSlider.TicksBelow)
        self.slider_band_size.setTickInterval(5)
        self.slider_band_size.valueChanged.connect(self.sizevaluechange)

        #List of bands
        self.bands_list.setColumnWidth(0, 230)
        self.bands_list.setColumnWidth(1, 230)
        self.bands_list.setColumnWidth(2, 80)
        self.but_add_band.clicked.connect(self.add_to_bands_list)
        self.bands_list.doubleClicked.connect(self.slot_double_clicked)

        self.but_run.clicked.connect(self.add_bands_to_map)
        self.add_fields_to_cboxes()
        self.random_rgb()

    def spacevaluechange(self):
        self.space_size = self.slider_spacer.value() / 100.0
        self.lbl_space.setText("{:3,.2f}".format(self.space_size))

    def sizevaluechange(self):
        self.band_size = self.slider_band_size.value() / 5.0
        self.lbl_width.setText("{:3,.2f}".format(self.band_size))

    def slot_double_clicked(self, mi):
        row = mi.row()
        if row > -1:
            self.bands_list.removeRow(row)
            self.tot_bands -= 1

    def add_fields_to_cboxes(self):
        self.layer = get_vector_layer_by_name(self.mMapLayerComboBox.currentText())
        self.ab_FieldComboBox.setLayer(self.layer)
        self.ba_FieldComboBox.setLayer(self.layer)

    def add_to_bands_list(self):
        if self.ab_FieldComboBox.currentIndex() >= 0 and self.ba_FieldComboBox.currentIndex() >= 0:
            ab_band = self.layer.fieldNameIndex(self.ab_FieldComboBox.currentText())
            ba_band = self.layer.fieldNameIndex(self.ba_FieldComboBox.currentText())

            self.tot_bands += 1
            self.bands_list.setRowCount(self.tot_bands)

            self.bands_list.setItem(self.tot_bands - 1, 0, QTableWidgetItem(self.ab_FieldComboBox.currentText()))
            self.bands_list.setItem(self.tot_bands - 1, 1, QTableWidgetItem(self.ba_FieldComboBox.currentText()))
            self.bands_list.setItem(self.tot_bands - 1, 2, QTableWidgetItem(''))

            self.bands_list.item(self.tot_bands - 1, 2).setBackground(self.mColorButton.color())
            self.random_rgb()

    def random_rgb(self):
        rgb = []
        for i in range(3):
            rgb.append(randint(0, 255))
        a = QColor()
        a.setRgb(rgb[0], rgb[1], rgb[2])
        self.mColorButton.setColor(a)

    def add_bands_to_map(self):
        self.but_run.setEnabled(False)
        self.band_size = str(self.band_size)
        self.space_size = str(self.space_size)

        # define the side of the plotting based on the side of the road the system has defined
        ab = -1
        if self.drive_side == 'right':
            ab = 1
        ba = - ab

        bands_ab = []
        bands_ba = []
        # go through all the fields that will be used to find the maximum value. This will be used
        # to limit the size of bandwidth for all layers of bands
        values = []
        for i in range(self.tot_bands):
            for j in range(2):
                field = self.bands_list.item(i, j).text()
                idx = self.layer.fieldNameIndex(field)
                values.append(self.layer.maximumValue(idx))

                # we also build a list of bands to construct
                # The function "(2 * j -1) * ba"  maps the index j {1,2} and the direction to the side of the
                # link the band needs to be. Try it out. it works!!
                #bands.append((field, (2 * j -1) * ba, self.bands_list.item(i, 2).backgroundColor()))
            cl = self.bands_list.item(i, 2).backgroundColor()
            bands_ab.append((self.bands_list.item(i, 0).text(), ab, cl))
            bands_ba.append((self.bands_list.item(i, 1).text(), ba, cl))
        sides = [bands_ab, bands_ba]
        max_value = max(values)

        for s in sides:
            acc_offset = '0'
            for field, side, clr in s:
                symbol_layer = QgsSimpleLineSymbolLayerV2.create({})
                props = symbol_layer.properties()
                width = '(coalesce(scale_linear("' + field + '", 0, ' + str(max_value) + ', 0, ' + self.band_size + '), 0))'
                props['width_dd_expression'] = width

                props['offset_dd_expression'] = acc_offset + '+' + str(side) + ' * (coalesce(scale_linear("' + field + \
                                                '", 0, ' + str(max_value) + ', 0, ' + self.band_size + '), 0)/2 + ' + \
                                                self.space_size + ')'

                props['line_color'] = str(clr.getRgb()[0]) + ',' + str(clr.getRgb()[1]) + ',' + str(clr.getRgb()[2]) + ',' \
                                      + str(clr.getRgb()[3])
                symbol_layer = QgsSimpleLineSymbolLayerV2.create(props)
                self.layer.rendererV2().symbol().appendSymbolLayer(symbol_layer)

                acc_offset = acc_offset + ' + ' + str(side) + '*(' + width + '+' + self.space_size + ')'

        self.layer.triggerRepaint()
        self.exit_procedure()

    def exit_procedure(self):
        self.close()

if __name__ == '__main__':
    main()