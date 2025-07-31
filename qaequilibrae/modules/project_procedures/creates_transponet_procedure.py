from string import ascii_letters

import numpy as np
from PyQt5.QtCore import pyqtSignal
from aequilibrae import Project
from aequilibrae.context import get_logger
from aequilibrae.utils.interface.worker_thread import WorkerThread

from qaequilibrae.modules.common_tools.geodataframe_from_data_layer import geodataframe_from_layer

logger = get_logger()


class CreatesTranspoNetProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, proj_folder, node_layer, node_fields, link_layer, link_fields):
        WorkerThread.__init__(self, parentThread)

        self.proj_folder = proj_folder
        self.node_fields = node_fields
        self.link_fields = link_fields
        self.node_layer = node_layer
        self.link_layer = link_layer
        self.report = []
        self.project: Project

    def doWork(self):
        self.signal.emit(["start", 5, self.tr("Initializing project")])
        self.project = Project()
        self.project.new(self.proj_folder)
        self.signal.emit(["update", 1, "Project created"])

        # Add the required extra fields to the link layer
        self.signal.emit(["update", 2, self.tr("Adding extra fields to links layer")])
        self.additional_fields_to_layers("links", self.link_layer, self.link_fields)
        self.signal.emit(["update", 3, self.tr("Adding extra fields to nodes layer")])
        self.additional_fields_to_layers("nodes", self.node_layer, self.node_fields)

        self.signal.emit(["update", 4, self.tr("Building links layer")])
        self.transfer_layer_features("links", self.link_layer, self.link_fields)

        self.signal.emit(["update", 5, self.tr("Renumbering nodes layer")])
        self.renumber_nodes()

        self.signal.emit(["finished"])

    # Adds the non-standard fields to a layer
    def additional_fields_to_layers(self, table, layer, layer_fields):
        fields = layer.dataProvider().fields()

        data = self.project.network.links if table == "links" else self.project.network.nodes

        existing_fields = data.data.columns.tolist()

        for f in set(layer_fields.keys()):
            if f.lower() in existing_fields:
                continue
            field = fields[layer_fields[f]]
            if not field.isNumeric():
                field_type = "TEXT"
            else:
                field_type = "INTEGER" if "integer" in field.typeName() else "REAL"
            data.fields.add(f, "Field automatically added during project creation from layers", field_type)

        data.refresh_fields()

    def renumber_nodes(self):
        nodes = self.project.network.nodes.data
        nodes = nodes[["node_id", "geometry"]]
        nodes.columns = ["nid", "geometry"]

        gdf = geodataframe_from_layer(self.node_layer)
        # We ensure that `is_centroid` is always integer
        cnt = gdf.columns[self.node_fields["is_centroid"]]
        gdf[cnt] = gdf[cnt].astype(np.int64)

        columns = [gdf.columns.tolist()[idx] for idx in self.node_fields.values() if idx >= 0]
        columns.extend(["geometry"])
        gdf = gdf[columns]

        gdf = gdf.sjoin(nodes)
        gdf.drop(columns={"geometry", "index_right"}, inplace=True)

        flds = list(self.node_fields.keys())
        setting = [f"{fld}=?" for fld in flds if fld != "node_id"]
        sql_values = f'UPDATE nodes SET {",".join(setting)} WHERE node_id=?;'

        sql_id = "UPDATE nodes SET node_id=? WHERE node_id=?;"

        with self.project.db_connection_spatial as conn:
            conn.executemany(sql_values, gdf.iloc[:, 1:].to_records(index=False))
            conn.executemany(sql_id, gdf.iloc[:, :1].join(gdf.iloc[:, -1:]).to_records(index=False))

    def transfer_layer_features(self, table, layer, layer_fields):
        # We ensure that `link_id`, `a_node`, `b_node`, and `direction` fields are always integers
        gdf = geodataframe_from_layer(layer).infer_objects()

        all_modes = set("".join(gdf.iloc[:, layer_fields["modes"]].unique()))
        all_link_types = gdf.iloc[:, layer_fields["link_type"]].unique()
        self.__add_linktypes_and_modes(all_link_types, all_modes)

        crs = int(layer.crs().authid().split(":")[1])
        fields = [k for k, v in layer_fields.items() if v >= 0]
        field_titles = ",".join(fields)
        sql = f"""INSERT INTO {table} ({field_titles},geometry)
                  VALUES ({','.join(['?'] * len(fields))},GeomFromWKB(?, {crs}))"""

        columns = [gdf.columns.tolist()[idx] for idx in layer_fields.values() if idx >= 0]
        columns.extend(["geoms"])

        gdf = gdf[columns]

        with self.project.db_connection_spatial as conn:
            conn.executemany(sql, gdf.to_records(index=False))

    def __add_linktypes_and_modes(self, all_link_types, all_modes):
        # We check if all modes exist
        modes = self.project.network.modes
        current_modes = list(modes.all_modes().keys())
        all_modes = [x for x in all_modes if x not in current_modes]
        for md in all_modes:
            new_mode = modes.new(md)
            new_mode.mode_name = md
            new_mode.description = "Mode automatically added during project creation from layers"
            modes.add(new_mode)
            new_mode.save()
            logger.info(f"{new_mode.description} --> ({md})")

        # We check if all link types exist
        link_types = self.project.network.link_types
        current_lt = [lt.link_type for lt in link_types.all_types().values()]
        letters = [x for x in list(ascii_letters) if x not in link_types.all_types().keys()]
        all_link_types = [lt for lt in all_link_types if lt not in current_lt]
        logger.info(all_link_types)
        for lt in all_link_types:
            new_link_type = link_types.new(letters[0])
            letters = letters[1:]
            new_link_type.link_type = lt
            new_link_type.description = "Link type automatically added during project creation from layers"
            new_link_type.save()
            logger.info(new_link_type.description + f" --> ({new_link_type.link_type})")
