"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Procedure for creating a TranspoNet from layers previously prepared
 Purpose:    TranspoNet creation

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE
 Transponet Repository: https://github.com/AequilibraE/TranspoNet

 Created:    2017-05-03
 Updated:    2020-02-08
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from shutil import copyfile
from qgis.core import *
from qgis.PyQt.QtCore import *
from ..common_tools.auxiliary_functions import *
from ..common_tools.global_parameters import *
from ..common_tools import WorkerThread
from aequilibrae.project import Project
from aequilibrae import logger


class CreatesTranspoNetProcedure(WorkerThread):
    def __init__(
            self,
            parentThread,
            output_file,
            node_layer,
            node_fields,
            link_layer,
            link_fields,
    ):
        WorkerThread.__init__(self, parentThread)

        self.output_file = output_file
        self.node_fields = node_fields
        self.link_fields = link_fields
        self.node_layer = node_layer
        self.link_layer = link_layer
        self.report = []
        self.project: Project

    def doWork(self):
        self.emit_messages(message="Initializing project", value=0, max_val=1)
        self.project = Project(self.output_file, True)
        self.project.conn.close()
        self.project.conn = qgis.utils.spatialite_connect(self.output_file)
        self.project.network.conn = self.project.conn
        self.project.network.create_empty_tables()

        # Add the required extra fields to the link layer
        self.emit_messages(message="Adding extra network data fields to database", value=0, max_val=1)
        self.additional_fields_to_layers('links', self.link_layer, self.link_fields)
        self.additional_fields_to_layers('nodes', self.node_layer, self.node_fields)

        conn = qgis.utils.spatialite_connect(self.output_file)

        self.transfer_layer_features("links", self.link_layer, self.link_fields)
        self.transfer_layer_features("nodes", self.node_layer, self.node_fields)

        self.emit_messages(message="Creating layer triggers", value=0, max_val=1)
        self.project.network.add_triggers()
        self.emit_messages(message="Spatial indices", value=0, max_val=1)
        self.project.network.add_spatial_index()
        self.ProgressText.emit("DONE")

    # Adds the non-standard fields to a layer
    def additional_fields_to_layers(self, table, layer, layer_fields):
        curr = self.project.conn.cursor()
        fields = layer.dataProvider().fields()
        string_fields = []

        curr.execute(f'PRAGMA table_info({table});')
        field_names = curr.fetchall()
        existing_fields = [f[1].lower() for f in field_names]

        for f in set(layer_fields.keys()):
            if f in existing_fields:
                continue
            field = fields[layer_fields[f]]
            field_length = field.length()
            if not field.isNumeric():
                field_type = "char"
                string_fields.append(f)
            else:
                if "Int" in field.typeName():
                    field_type = "INTEGER"
                else:
                    field_type = "REAL"
            try:
                sql = "alter table " + table + " add column " + f + " " + field_type + "(" + str(field_length) + ")"
                curr.execute(sql)
                self.project.conn.commit()
            except:
                logger.error(sql)
                self.report.append("field " + str(f) + " could not be added")
        curr.close()
        return string_fields

    def transfer_layer_features(self, table, layer, layer_fields):
        self.emit_messages(message=f"Transferring features from {table} layer", value=0, max_val=layer.featureCount())
        curr = self.project.conn.cursor()

        field_titles = ", ".join(list(layer_fields.keys()))
        all_modes = set()
        for j, f in enumerate(layer.getFeatures()):
            self.emit_messages(value=j)
            attrs = []
            for k, val in layer_fields.items():
                if val < 0:
                    attrs.append("NULL")
                else:
                    attr_val = self.convert_data(f.attributes()[val])
                    if not str(attr_val).isnumeric():
                        attrs.append(f'"{attr_val}"')
                    else:
                        attrs.append(attr_val)

            attrs = ", ".join(attrs)
            geom = f.geometry().asWkt().upper()
            crs = str(layer.crs().authid().split(":")[1])

            sql = f"INSERT INTO {table} ({field_titles} , geometry)  VALUES ({attrs} , GeomFromText('{geom}', {crs}))"

            if table == 'links':
                all_modes.update(list(f.attributes()[layer_fields['modes']]))
            try:
                curr.execute(sql)
            except:
                if f.id():
                    msg = "feature with id " + str(f.id()) + " could not be added to layer " + table
                else:
                    msg = "feature with no node id present. It could not be added to layer " + table
                self.report.append(msg)

        # We check if all modes exist
        a = self.project.network.modes()
        for x in all_modes:
            if x not in a:
                par = [f'"automatic_{x}"', f'"{x}"', '"Mode automatically added during project creation from layers"']
                curr.execute(f'INSERT INTO "modes" (mode_name, mode_id, description) VALUES({",".join(par)})')
                logger.info(f'New mode inserted during project creation {x}')
        self.project.conn.commit()
        curr.close()

    def convert_data(self, value):
        if type(value) == NULL:
            return "NULL"
        else:
            return str(value).replace('"', "'")

    def emit_messages(self, message="", value=-1, max_val=-1):
        if len(message) > 0:
            self.ProgressText.emit(message)
        if value >= 0:
            self.ProgressValue.emit(value)
        if max_val >= 0:
            self.ProgressMaxValue.emit(max_val)
