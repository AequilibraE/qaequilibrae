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
 Updated:    
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

from qgis.core import *
from PyQt4.QtCore import *
from ..common_tools.auxiliary_functions import *
from pyspatialite import dbapi2 as db
from ..common_tools.global_parameters import *
from ..common_tools import WorkerThread


class CreatesTranspoNetProcedure(WorkerThread):
    def __init__(self, parentThread, output_file, node_fields, link_fields, node_layer, required_fields_nodes,
                 node_field_indices, link_layer, required_fields_links, link_field_indices):
        WorkerThread.__init__(self, parentThread)

        self.output_file = output_file
        self. node_fields = node_fields
        self.link_fields = link_fields
        self.node_layer = node_layer
        self.required_fields_nodes = required_fields_nodes
        self.node_field_indices = node_field_indices
        self.link_layer = link_layer
        self.required_fields_links = required_fields_links
        self.link_field_indices = link_field_indices
        self.report = []

    def doWork(self):
        nfields = ", ".join(self.node_fields)
        lfields = ", ".join(self.link_fields)
        self.emit_messages(message='Sit tight. Initializing Spatialite layer set', value=0, max_val=1)
        self.run_series_of_queries(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'queries_for_empty_file.sql'))

        conn = db.connect(self.output_file)

        self.emit_messages(message='Adding non-mandatory link fields', value=0, max_val=1)

        link_string_fields = self.adds_non_standard_fields_to_layers(conn, 'links', self.link_layer, self.link_fields,
                                                                     self.required_fields_links,
                                                                     self.link_field_indices)

        self.emit_messages(message='Adding non-mandatory node fields', value=0, max_val=1)
        node_string_fields = self.adds_non_standard_fields_to_layers(conn, 'nodes', self.node_layer, self.node_fields,
                                                                     self.required_fields_nodes, self.node_field_indices)

        self.transfer_layer_features(conn, 'links', self.link_layer, self.link_fields, self.link_field_indices,
                                     link_string_fields, lfields)

        self.transfer_layer_features(conn, 'nodes', self.node_layer, self.node_fields, self.node_field_indices,
                                node_string_fields, nfields)

        self.emit_messages(message = 'Creating layer triggers', value = 0, max_val=1)
        # DONE
        self.run_series_of_queries(
           os.path.join(os.path.dirname(os.path.abspath(__file__)), 'triggers.sql'))

        self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), "DONE")

    # Adds the non-standard fields to a layer
    def adds_non_standard_fields_to_layers(self, conn, table, layer, layer_fields, required_fields, field_indices):
        curr = conn.cursor()
        fields = layer.pendingFields()
        string_fields = []
        for f in layer_fields:
            if f not in required_fields:
                field = fields[field_indices[f]]
                field_length = field.length()
                if not field.isNumeric():
                    field_type = 'char'
                    string_fields.append(field_indices[f])
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

    def transfer_layer_features(self, conn, table, layer, layer_fields, field_indices, string_fields, field_titles):
        self.emit_messages(message='Transferring features from ' + table + "' layer", value=0, max_val=layer.featureCount())
        curr = conn.cursor()
        # We add the Nodes layer
        for j, f in enumerate(layer.getFeatures()):
            self.emit_messages(value=j)
            attrs = []
            for q in layer_fields:
                if field_indices[q] in string_fields:
                    attrs.append("'" + f.attributes()[field_indices[q]] + "'")
                else:
                    attrs.append(str(f.attributes()[field_indices[q]]))
            attrs = ', '.join(attrs)
            sql = 'INSERT INTO ' + table + ' (' + field_titles + ', geometry) '
            sql += "VALUES (" + attrs + ", "
            sql += "GeomFromText('" + f.geometry().exportToWkt().upper() + "', " + str(
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

    def emit_messages(self, message='', value = -1, max_val = -1):
        if len(message) > 0:
            self.emit(SIGNAL("ProgressText (PyQt_PyObject)"), message)
        if value >= 0:
            self.emit(SIGNAL("ProgressValue(PyQt_PyObject)"), value)
        if max_val >= 0:
            self.emit(SIGNAL("ProgressMaxValue(PyQt_PyObject)"), max_val)

    def run_series_of_queries(self, queries):

        conn = db.connect(self.output_file)
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
                curr.execute(cmd)
            except:
                self.report.append( 'query error: ' + cmd)
        conn.commit()
        conn.close()
