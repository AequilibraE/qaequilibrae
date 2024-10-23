import numpy as np
from PyQt5.QtCore import pyqtSignal
from qgis._core import QgsField, QgsFeatureRequest, QgsPointXY, QgsVectorLayer, QgsGeometry, QgsFeature, QgsSpatialIndex

from qgis.PyQt.QtCore import QVariant
from aequilibrae.utils.interface.worker_thread import WorkerThread
from qaequilibrae.modules.common_tools import get_vector_layer_by_name


class NetworkPreparationProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(
        self,
        parentThread,
        line_layer,
        new_line_layer,
        node_layer=False,
        node_ids=False,
        new_node_layer=False,
        node_start=0,
    ):
        WorkerThread.__init__(self, parentThread)
        self.line_layer = line_layer
        self.node_layer = node_layer
        self.node_ids = node_ids
        self.new_node_layer = new_node_layer
        self.new_line_layer = new_line_layer
        self.node_start = node_start
        self.error = None
        self.report = []
        self.epsg_code = 4326

    def doWork(self):
        line_layer = self.line_layer
        node_layer = self.node_layer
        node_ids = self.node_ids
        layer = get_vector_layer_by_name(line_layer)
        feat_count = layer.featureCount()

        self.signal.emit(["set_text", 0, 0, self.tr("Duplicating line layer"), "master"])

        # We create the new line layer and load it in memory
        self.epsg_code = int(layer.crs().authid().split(":")[1])
        new_line_layer = self.duplicate_layer(layer, "Linestring", self.new_line_layer)
        self.signal.emit(["set_text", 0, 0, self.tr("Line layer duplicated"), "master"])

        # Add the A_Node and B_node fields to the layer
        field_names = [x.name().upper() for x in new_line_layer.dataProvider().fields().toList()]
        add_fields = ["A_NODE", "B_NODE"]
        for f in add_fields:
            if f not in field_names:
                _ = new_line_layer.dataProvider().addAttributes([QgsField(f, QVariant.Int)])
        new_line_layer.updateFields()
        self.signal.emit(["set_text", 0, 0, self.tr("Adding fields to line layer"), "master"])
        # If we have node IDs, we iterate over the ID field to make sure they are unique

        if node_ids:
            self.with_node_ids(feat_count, new_line_layer, node_ids, node_layer)
        else:
            self.with_lines_only(feat_count, new_line_layer)

        self.signal.emit(["finished"])

    def with_lines_only(self, feat_count, new_line_layer):
        #  Create node layer
        new_node_layer = QgsVectorLayer(
            f"Point?crs=epsg:{self.epsg_code}&field=ID:integer", self.new_node_layer, "memory"
        )
        DTYPE = [
            ("LAT", np.float64),
            ("LONG", np.float64),
            ("LINK ID", np.int64),
            ("POSITION", np.int64),
            ("NODE ID", np.int64),
        ]
        all_nodes = np.zeros(feat_count * 2, dtype=DTYPE)
        line = 0
        txt = self.tr("Links read: {}/{}")
        self.signal.emit(["start", 0, feat_count, txt.format(0, feat_count), "master"])

        #  Let's read all links and the coordinates for their extremities
        for p, feat in enumerate(new_line_layer.getFeatures()):
            if p % 500 == 0:
                self.signal.emit(["update", 0, p, txt.format(p, feat_count), "master"])

            link = list(feat.geometry().asPolyline())
            if link:
                link_id = feat.id()

                node_a = (round(link[0][0], 10), round(link[0][1], 10))
                node_b = (round(link[-1][0], 10), round(link[-1][1], 10))

                all_nodes[line][0] = node_a[0]
                all_nodes[line][1] = node_a[1]
                all_nodes[line][2] = link_id
                all_nodes[line][3] = 0
                line += 1
                all_nodes[line][0] = node_b[0]
                all_nodes[line][1] = node_b[1]
                all_nodes[line][2] = link_id
                all_nodes[line][3] = 1
                line += 1

        self.signal.emit(["update", 0, feat_count, txt.format(feat_count, feat_count), "master"])

        # Now we sort the nodes and assign IDs to them
        all_nodes = np.sort(all_nodes, order=["LAT", "LONG"])
        lat0 = -100000.0
        longit0 = -100000.0
        incremental_ids = self.node_start - 1
        p = 0
        txt = self.tr("Computing node IDs: {}/{}")
        self.signal.emit(["start", 0, int(feat_count * 2), txt.format(0, feat_count * 2), "master"])
        for i in all_nodes:
            p += 1
            lat, longit, link_id, position, node_id = i

            if lat != lat0 or longit != longit0:
                incremental_ids += 1
                lat0 = lat
                longit0 = longit

            i[4] = incremental_ids

            if p % 2000 == 0:
                self.signal.emit(["update", 0, p, txt.format(p, int(feat_count * 2)), "master"])

        self.signal.emit(
            ["update", 0, int(feat_count * 2), txt.format(int(feat_count * 2), int(feat_count * 2)), "master"]
        )

        # And we write the node layer as well
        node_id0 = -1
        p = 0
        txt = self.tr("Writing new node layer: {}/{}")
        self.signal.emit(["start", 0, incremental_ids, txt.format(0, incremental_ids), "master"])
        cfeatures = []
        for i in all_nodes:
            lat, longit, link_id, position, node_id = i

            if node_id != node_id0:
                p += 1
                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lat, longit)))
                feature.setAttributes([int(node_id)])
                cfeatures.append(feature)
                node_id0 = node_id

            if p % 500 == 0:
                self.signal.emit(["update", 0, incremental_ids, txt.format(p, incremental_ids), "master"])
        _ = new_node_layer.dataProvider().addFeatures(cfeatures)
        del cfeatures
        new_node_layer.commitChanges()
        self.signal.emit(["update", 0, incremental_ids, txt.format(incremental_ids, incremental_ids), "master"])

        # Now we write all the node _IDs back to the line layer
        txt = self.tr("Writing node IDs to links: {}/{}")
        self.signal.emit(["start", 0, int(feat_count * 2), txt.format(0, int(feat_count * 2)), "master"])
        fid1 = new_line_layer.dataProvider().fieldNameIndex("A_NODE")
        fid2 = new_line_layer.dataProvider().fieldNameIndex("B_NODE")
        for p, i in enumerate(all_nodes):
            lat, longit, link_id, position, node_id = i

            if position == 0:
                new_line_layer.dataProvider().changeAttributeValues({int(link_id): {fid1: int(node_id)}})
            else:
                new_line_layer.dataProvider().changeAttributeValues({int(link_id): {fid2: int(node_id)}})

            if p % 50 == 0:
                self.signal.emit(["update", 0, int(p), txt.format(p, int(feat_count * 2)), "master"])

        self.signal.emit(
            ["update", 0, int(feat_count * 2), txt.format(int(feat_count * 2), int(feat_count * 2)), "master"]
        )

        new_line_layer.commitChanges()
        self.new_line_layer = new_line_layer
        self.new_node_layer = new_node_layer

    def with_node_ids(self, feat_count, new_line_layer, node_ids, node_layer):
        ids = []
        nodes = get_vector_layer_by_name(node_layer)
        index = QgsSpatialIndex()
        idx = nodes.dataProvider().fieldNameIndex(node_ids)
        self.signal.emit(["start", 0, nodes.featureCount(), "Checking node layer", "master"])
        for P, feat in enumerate(nodes.getFeatures()):
            txt = self.tr("Checking node layer: {}/{}").format(str(P), str(nodes.featureCount()))
            self.signal.emit(["update", 0, P, txt, "master"])
            index.addFeature(feat)
            i_d = feat.attributes()[idx]
            if i_d in ids:
                self.error = f"ID {str(i_d)} is non unique in your selected field"
                self.report.append(self.error)
            if i_d < 0:
                self.error = "Negative node ID in your selected field"
                self.report.append(self.error)
                break
            ids.append(i_d)
        if self.error is None:
            self.signal.emit(["start", 0, new_line_layer.featureCount(), "Processing links", "master"])
            P = 0
            for feat in new_line_layer.getFeatures():
                P += 1
                txt = self.tr("Processing links: {}/{}").format(str(P), str(feat_count))
                self.signal.emit(["update", 0, int(P), txt, "master"])

                # We search for matches for all AB nodes
                ab_nodes = [("A_NODE", 0), ("B_NODE", -1)]
                for field, position in ab_nodes:
                    node_ab = list(feat.geometry().asPolyline())[position]
                    # We compute the closest node
                    nearest = index.nearestNeighbor(QgsPointXY(node_ab), 1)

                    # We get coordinates on this node
                    fid = nearest[0]
                    nfeat = nodes.getFeatures(QgsFeatureRequest(fid)).__next__()
                    nf = nfeat.geometry().asPoint()

                    fid = new_line_layer.dataProvider().fieldNameIndex(field)

                    if round(nf[0], 10) == round(node_ab[0], 10) and round(nf[1], 10) == round(node_ab[1], 10):
                        ids = nfeat.attributes()[idx]
                        new_line_layer.dataProvider().changeAttributeValues({feat.id(): {fid: int(ids)}})

                    else:  # If not, we throw an error
                        self.error = f"CORRESPONDING NODE NOT FOUND. Link: {str(feat.attributes())}"
                        self.report.append(self.error)
                        break
                if self.error is not None:
                    break

                new_line_layer.commitChanges()
                self.new_line_layer = new_line_layer

    def duplicate_layer(self, original_layer, layer_type, layer_name):
        self.epsg_code = int(original_layer.crs().authid().split(":")[1])
        feats = [feat for feat in original_layer.getFeatures()]
        duplicate_layer = QgsVectorLayer(layer_type + "?crs=epsg:" + str(self.epsg_code), layer_name, "memory")
        new_layer_data = duplicate_layer.dataProvider()
        attr = original_layer.dataProvider().fields().toList()
        new_layer_data.addAttributes(attr)
        duplicate_layer.updateFields()
        new_layer_data.addFeatures(feats)
        del feats
        return duplicate_layer
