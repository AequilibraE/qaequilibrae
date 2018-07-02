"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Accessory interface for the bandwidth map
 Purpose:    Set scale for bandwith map

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2017-7-24
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import copy
import qgis
from qgis.core import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt import uic

from ..common_tools.auxiliary_functions import *
from ..common_tools.global_parameters import *


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__),  'forms/ui_bandwitdth_scale.ui'))

class BandwidthScaleDialog(QDialog, FORM_CLASS):
    def __init__(self, iface, layer, scale, default_scale):
        QDialog.__init__(self)
        self.iface = iface
        self.setupUi(self)
        
        self.scale = scale
        self.layer = layer
        self.default_scale = default_scale

        self.box_ref_value.setText("{:3,}".format(self.scale['max_flow']))
        
        # space slider
        self.slider_spacer.setMinimum(0)
        self.slider_spacer.setMaximum(100)
        self.slider_spacer.setValue(self.scale['spacing'] * 100)
        self.slider_spacer.setTickPosition(QSlider.TicksBelow)
        self.slider_spacer.setTickInterval(5)

        # band slider
        self.slider_band_size.setMinimum(5)
        self.slider_band_size.setMaximum(300)
        self.slider_band_size.setValue(self.scale['width'] * 10)
        self.slider_band_size.setTickPosition(QSlider.TicksBelow)
        self.slider_band_size.setTickInterval(10)

        self.slider_spacer.valueChanged.connect(self.spacevaluechange)
        self.slider_band_size.valueChanged.connect(self.sizevaluechange)

        self.chb_dual.toggled.connect(self.add_fields_to_combobox)
        
        self.but_reset.clicked.connect(self.reset_scale)
        self.but_use_default.clicked.connect(self.use_default)
        self.but_set_scale.clicked.connect(self.exit_procedure)
        
        self.add_fields_to_combobox()

        self.spacevaluechange()
        self.sizevaluechange()

    def add_fields_to_combobox(self):
        self.cbb_field_to_scale_from.clear()
        fields = []
        for field in self.layer.dataProvider().fields().toList():
            if field.type() in integer_types + float_types:
                fields.append(field.name())

        if self.chb_dual.isChecked():
            for field in fields:
                if '_ab' in field:
                    if field.replace('_ab', '_ba') in fields:
                        fields.remove(field.replace('_ab', '_ba'))
                        field = field.replace('_ab', '_*')
                        self.cbb_field_to_scale_from.addItem(field)
                elif '_ba' in field:
                    if field.replace('_ba', '_ab') in fields:
                        fields.remove(field.replace('_ba', '_ab'))
                        field = field.replace('_ba', '_*')
                        self.cbb_field_to_scale_from.addItem(field)
                else:
                    self.cbb_field_to_scale_from.addItem(field)
        else:
            for field in fields:
                self.cbb_field_to_scale_from.addItem(field)
    
    def use_default(self):
        self.scale = copy.deepcopy(self.default_scale)
        self.exit_procedure()

    def reset_scale(self):
        self.scale['width'] = self.default_scale['width']
        self.scale['spacing'] = self.default_scale['spacing']
        
        max_flow = -1
        if self.cbb_field_to_scale_from.currentIndex() > 0:
            if '_*' in self.cbb_field_to_scale_from.currentText():
                fields = [self.cbb_field_to_scale_from.currentText().replace('_*', '_ab'),
                          self.cbb_field_to_scale_from.currentText().replace('_*', '_ba')]
            else:
                fields = [self.cbb_field_to_scale_from.currentText()]
            
            for f in fields:
                idx = self.layer.dataProvider().fieldNameIndex(f)
                max_flow = max(max_flow, self.layer.maximumValue(idx))
                
        self.box_ref_value.setText("{:3,.2f}".format(max_flow))
        self.scale['max_flow'] = max_flow
        self.reset_sliders()
    
    def reset_sliders(self):
        self.slider_band_size.setValue(self.scale['width'] * 10)
        self.slider_spacer.setValue(self.scale['spacing'] * 100)

    def spacevaluechange(self):
        self.scale['spacing'] = self.slider_spacer.value() / 100.0
        self.lbl_space.setText("{:3,.2f}".format(self.scale['spacing']))

    def sizevaluechange(self):
        self.scale['width'] = self.slider_band_size.value() / 10.0
        self.lbl_width.setText("{:3,.2f}".format(self.scale['width']))
        
    def exit_procedure(self):
        self.scale['max_flow'] = float(self.box_ref_value.text().replace(',',''))
        self.close()