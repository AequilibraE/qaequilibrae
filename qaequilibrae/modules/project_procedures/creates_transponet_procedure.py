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
            if f.lower() in existing_fields or layer_fields[f] < 0:
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

        flds = [fld for fld, idx in self.node_fields.items() if idx >= 0]
        setting = [f"{fld}=?" for fld in flds if fld != "node_id"]
        # Only the column names are interpolated, and they are the keys of our own node_fields schema
        sql_values = f'UPDATE nodes SET {",".join(setting)} WHERE node_id=?;'  # nosec B608

        sql_id = "UPDATE nodes SET node_id=? WHERE node_id=?;"

        with self.project.db_connection_spatial as conn:
            conn.executemany(sql_values, gdf.iloc[:, 1:].to_records(index=False))
            conn.executemany(sql_id, gdf.iloc[:, :1].join(gdf.iloc[:, -1:]).to_records(index=False))

    def transfer_layer_features(self, table, layer, layer_fields):
        # We ensure that `link_id` and `direction` fields are always integers
        gdf = geodataframe_from_layer(layer).infer_objects()

        all_modes = set("".join(gdf.iloc[:, layer_fields["modes"]].unique()))
        all_link_types = gdf.iloc[:, layer_fields["link_type"]].unique()
        self.__add_linktypes_and_modes(all_link_types, all_modes)

        crs = int(layer.crs().authid().split(":")[1])
        fields = [k for k, v in layer_fields.items() if v >= 0]
        columns = [gdf.columns.tolist()[idx] for idx in layer_fields.values() if idx >= 0]

        # `link_id` does not need to come from the layer, in which case we number the links sequentially
        if layer_fields.get("link_id", -1) < 0:
            gdf = gdf.assign(__aeq_link_id__=np.arange(1, gdf.shape[0] + 1))
            fields.insert(0, "link_id")
            columns.insert(0, "__aeq_link_id__")

        # `a_node` and `b_node` are computed by the database triggers from the link geometry, but the links
        # table only accepts them as integers, so we seed them the same way AequilibraE itself does
        markers = ["?"] * len(fields)
        for fld in ["a_node", "b_node"]:
            if fld not in fields:
                fields.append(fld)
                markers.append("0")

        # Only the table and column names are interpolated, and they are the keys of our own layer_fields schema
        sql = f"""INSERT INTO {table} ({",".join(fields)},geometry)
                  VALUES ({",".join(markers)},GeomFromWKB(?, {crs}))"""  # nosec B608

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
