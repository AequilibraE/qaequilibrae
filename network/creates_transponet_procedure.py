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
 Updated:    2017-07-18
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from shutil import copyfile
from qgis.core import *
from qgis.PyQt.QtCore import *
from ..common_tools.auxiliary_functions import *
# from sqlite3 import dbapi2 as db
from ..common_tools.global_parameters import *
from ..common_tools import WorkerThread
from aequilibrae import spatialite_database


class CreatesTranspoNetProcedure(WorkerThread):
    def __init__(self, parentThread, output_file,
                                     node_layer, node_fields, required_fields_nodes, initializable_nodes,
                                     link_layer, link_fields, required_fields_links, initializable_links):
        WorkerThread.__init__(self, parentThread)

        self.output_file = output_file
        self.node_fields = node_fields
        self.link_fields = link_fields
        self.node_layer = node_layer
        self.required_fields_nodes = required_fields_nodes
        self.link_layer = link_layer
        self.required_fields_links = required_fields_links
        self.initializable_links = initializable_links
        self.initializable_nodes = initializable_nodes
        self.report = []

    def doWork(self):
        self.emit_messages(message='Sit tight. Initializing Spatialite layer set', value=0, max_val=1)
        
        copyfile(spatialite_database, self.output_file)
        self.run_series_of_queries(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'queries_for_empty_file.sql'))

        conn = qgis.utils.spatialite_connect(self.output_file)

        self.emit_messages(message='Adding non-mandatory link fields', value=0, max_val=1)

        link_string_fields = self.additional_fields_to_layers(conn, 'links', self.link_layer, self.link_fields,
                                                              self.required_fields_links)

        self.emit_messages(message='Adding non-mandatory node fields', value=0, max_val=1)
        node_string_fields = self.additional_fields_to_layers(conn, 'nodes', self.node_layer, self.node_fields,
                                                              self.required_fields_nodes)

        self.transfer_layer_features(conn, 'links', self.link_layer, self.link_fields, link_string_fields,
                                     self.initializable_links)

        self.transfer_layer_features(conn, 'nodes', self.node_layer, self.node_fields, node_string_fields,
                                     self.initializable_nodes)

        self.emit_messages(message = 'Creating layer triggers', value = 0, max_val=1)
        # DONE
        self.run_series_of_queries(
           os.path.join(os.path.dirname(os.path.abspath(__file__)), 'triggers.sql'))

        self.ProgressText.emit("DONE")

    # Adds the non-standard fields to a layer
    def additional_fields_to_layers(self, conn, table, layer, layer_fields, required_fields):
        curr = conn.cursor()
        fields = layer.fields()
        string_fields = []
        
        for f in set(layer_fields.keys()) - set(required_fields):
            field = fields[layer_fields[f]]
            field_length = field.length()
            if not field.isNumeric():
                field_type = 'char'
                string_fields.append(f)
            else:
                if 'Int' in field.typeName():
                    field_type = 'INTEGER'
                else:
                    field_type = 'REAL'
            try:
                sql = 'alter table ' + table + ' add column ' + f + ' ' + field_type + '(' + str(field_length) + ')'
                curr.execute(sql)
                conn.commit()
            except:
                self.report.append('field ' + str(f) + ' could not be added')
        curr.close()
        return string_fields

    def transfer_layer_features(self, conn, table, layer, layer_fields, string_fields, initializable_fields):
        self.emit_messages(message='Transferring features from ' + table + "' layer",
                           value=0,
                           max_val=layer.featureCount())
        curr = conn.cursor()
        
        # We add the Nodes layer
        field_titles = ", ".join(layer_fields.keys())
        for j, f in enumerate(layer.getFeatures()):
            self.emit_messages(value=j)
            attributes = []
            for k, val in layer_fields.items():
                if val < 0:
                    attributes.append(str(initializable_fields[k]))
                else:
                    if k in string_fields:
                        attributes.append('"' + self.convert_data(f.attributes()[val]) + '"')
                    else:
                        attributes.append(self.convert_data(f.attributes()[val]))
            
            
            attributes = ', '.join(attributes)
            sql = 'INSERT INTO ' + table + ' (' + field_titles + ', geometry) '
            sql += "VALUES (" + attributes + ", "
            sql += "GeomFromText('" + f.geometry().asWkt().upper() + "', " + str(
                layer.crs().authid().split(":")[1]) + "))"

            try:
                a = curr.execute(sql)
            except:
                if f.id():
                    msg = 'feature with id ' + str(f.id()) + ' could not be added to layer ' + table
                else:
                    msg = 'feature with no node id present. It could not be added to layer ' + table
                self.report.append(msg)
        conn.commit()
        curr.close()

    def convert_data(self, value):
        if type(value) == NULL:
            return 'NULL'
        else:
            return str(value).replace('"', "'")
            
    def emit_messages(self, message='', value = -1, max_val = -1):
        if len(message) > 0:
            self.ProgressText.emit(message)
        if value >= 0:
            self.ProgressValue.emit(value)
        if max_val >= 0:
            self.ProgressMaxValue.emit(max_val)

    def run_series_of_queries(self, queries):

        conn = qgis.utils.spatialite_connect(self.output_file)
        curr = conn.cursor()
        # Reads all commands
        sql_file = open(queries, 'r')
        query_list = sql_file.read()
        sql_file.close()
        # Split individual commands
        sql_commands_list = query_list.split('#')
        # Run one query/command at a time
        for cmd in sql_commands_list:
            try:
                curr.execute(self.sql_special_cases(cmd))
            except:
                self.report.append( 'query error: ' + cmd)
        conn.commit()
        conn.close()

    def sql_special_cases(self, cmd):
        if "DEFAULT_CRS" in cmd:
            if 'links' in cmd:
                cmd = cmd.replace("DEFAULT_CRS", str(self.link_layer.crs().authid().split(":")[1]))
            else:
                cmd = cmd.replace("DEFAULT_CRS", str(self.node_layer.crs().authid().split(":")[1]))
        return cmd