from PyQt5.QtCore import pyqtSignal
from aequilibrae.context import get_logger
from aequilibrae.project import Project
from aequilibrae.project.database_connection import database_connection
from aequilibrae.utils.db_utils import commit_and_close
from aequilibrae.utils.interface.worker_thread import WorkerThread
from string import ascii_letters

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
        self.signal.emit(["start", 0, 1, self.tr("Initializing project"), "master"])
        self.project = Project()
        self.project.new(self.proj_folder)
        self.signal.emit(["update", 0, 1, "Project created", "master"])

        # Add the required extra fields to the link layer
        self.signal.emit(["start", 0, 2, self.tr("Adding extra network data fields to database"), "master"])
        self.additional_fields_to_layers("links", self.link_layer, self.link_fields)
        self.signal.emit(["update", 0, 1, "Added additional fields", "master"])
        self.additional_fields_to_layers("nodes", self.node_layer, self.node_fields)
        self.signal.emit(["update", 0, 2, "Added additional fields", "master"])

        self.transfer_layer_features("links", self.link_layer, self.link_fields)
        self.renumber_nodes()

        self.signal.emit(["set_text", 0, 0, self.tr("Creating layer triggers"), "master"])
        self.signal.emit(["set_text", 0, 0, self.tr("Spatial indices"), "master"])
        self.signal.emit(["finished"])

    # Adds the non-standard fields to a layer
    def additional_fields_to_layers(self, table, layer, layer_fields):
        with commit_and_close(database_connection("network")) as conn:

            fields = layer.dataProvider().fields()
            string_fields = []

            field_names = conn.execute(f"PRAGMA table_info({table});").fetchall()
            existing_fields = [f[1].lower() for f in field_names]

            for f in set(layer_fields.keys()):
                if f.lower() in existing_fields:
                    continue
                field = fields[layer_fields[f]]
                field_length = field.length()
                if not field.isNumeric():
                    field_type = "char"
                    string_fields.append(f)
                else:
                    field_type = "INTEGER" if "Int" in field.typeName() else "REAL"
                try:
                    sql = "alter table " + table + " add column " + f + " " + field_type + "(" + str(field_length) + ")"
                    conn.execute(sql)
                    self.project.conn.commit()
                except Exception as e:
                    logger.error(sql)
                    logger.error(e.args)
                    self.report.append(f"field {str(f)} could not be added")

        return string_fields

    def renumber_nodes(self):
        max_val = self.node_layer.maximumValue(self.node_fields["node_id"])
        with commit_and_close(database_connection("network")) as conn:
            num_nodes = conn.execute("select max(node_id) from nodes").fetchone()[0]
            max_val += num_nodes
            logger.info(max_val)

            conn.execute("BEGIN;")
            conn.execute("Update Nodes set node_id=node_id+?", [max_val])
            conn.execute("COMMIT;")

            self.signal.emit(["start", 0, self.node_layer.featureCount(), self.tr("Transferring nodes"), "master"])

            find_sql = """SELECT node_id
                            FROM nodes
                            WHERE geometry = GeomFromWKB(?, ?) AND
                            ROWID IN (
                            SELECT ROWID FROM SpatialIndex WHERE f_table_name = 'nodes' AND
                            search_frame = GeomFromWKB(?, ?))"""

            flds = list(self.node_fields.keys())
            setting = [f"{fld}=?" for fld in flds]
            update_sql = f'Update nodes set {",".join(setting)} where node_id=?'

            crs = int(self.node_layer.crs().authid().split(":")[1])
            for j, f in enumerate(self.node_layer.getFeatures()):
                self.signal.emit(["update", 0, j + 1, f"Feature: {j}", "master"])
                attrs = [
                    self.convert_data(f.attributes()[val]) if val >= 0 else None for val in self.node_fields.values()
                ]
                wkb = f.geometry().asWkb().data()
                node_id = conn.execute(find_sql, [wkb, crs, wkb, crs]).fetchall()
                if not node_id:
                    continue
                attrs.append(node_id)
                logger.info([update_sql, attrs])
            conn.commit()

    def transfer_layer_features(self, table, layer, layer_fields):
        self.signal.emit(["start", 0, layer.featureCount(), self.tr("Transferring {}").format(table), "master"])

        field_titles = ",".join(layer_fields.keys())
        all_modes = set()
        all_link_types = set()
        data_to_add = []
        sql = f"""INSERT INTO {table} ({field_titles} , geometry)
                  VALUES ({','.join(['?'] * len(layer_fields.keys()))},GeomFromWKB(?, ?))"""

        crs = int(layer.crs().authid().split(":")[1])

        for j, f in enumerate(layer.getFeatures()):
            self.signal.emit(["update", 0, j + 1, f"Feature: {j}", "master"])
            attrs = [self.convert_data(f.attributes()[val]) if val >= 0 else None for val in layer_fields.values()]
            attrs.extend([f.geometry().asWkb().data(), crs])
            data_to_add.append(attrs)

            if table == "links":
                all_modes.update(list(f.attributes()[layer_fields["modes"]]))
                all_link_types.update([f.attributes()[layer_fields["link_type"]]])

        with commit_and_close(database_connection("network")) as conn:
            if table == "links":
                self.__add_linktypes_and_modes(all_link_types, all_modes, conn)

            for data in data_to_add:
                try:
                    conn.execute(sql, data)
                except Exception as e:
                    logger.info(f"Failed inserting record {data[0]} for {table}")
                    logger.info(e.args)
                    logger.info([sql, data])
                    if data[0]:
                        msg = f"feature with id {data[0]} could not be added to layer {table}"
                    else:
                        msg = f"feature with no node id present. It could not be added to layer {table}"
                    self.report.append(msg)

    def __add_linktypes_and_modes(self, all_link_types, all_modes, conn):
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
        conn.commit()
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
            new_link_type.description = "Link_type automatically added during project creation from layers"
            new_link_type.save()
            logger.info(new_link_type.description + f" --> ({new_link_type.link_type})")
        conn.commit()

    def convert_data(self, value):
        return None if type(value) is None else value
