from functools import partial

from qgis.PyQt.QtCore import QCoreApplication, QSettings, QTimer
from qgis.core import Qgis, QgsFeature, QgsGeometry, QgsProject, QgsVectorLayer, QgsWkbTypes

# Kept in QSettings rather than in the project, since it is about how the user digitizes
SPLIT_SETTING = "qaequilibrae/split_links_at_nodes"

ID_FIELDS = ("ogc_fid", "link_id")


class LinkSplitter:
    """Breaks a link digitized across existing nodes into one link per stretch between them.

    Snapping is vertex only (see ``EditSnapping``), so a vertex dropped on a node carries that
    node's coordinates exactly, and an exact match against the nodes table is what decides where
    to break. Matching loosely would be worse than not matching at all: the triggers that fill
    ``a_node`` and ``b_node`` compare the endpoint to the nodes table with the same equality, so a
    break they disagreed with would leave a brand new node sitting a hair away from an existing
    one. Failing to match, on the other hand, just leaves the link whole.

    Nothing is done to the links the new one crosses: passing through a node connects the network
    there, while crossing a link where no node exists is a topology problem this cannot see, let
    alone fix.
    """

    def __init__(self, qgis_project):
        self.qgis_project = qgis_project
        self.watched = set()
        self.splitting = False

    @staticmethod
    def enabled() -> bool:
        return QSettings().value(SPLIT_SETTING, True, type=bool)

    @staticmethod
    def set_enabled(enabled: bool) -> None:
        QSettings().setValue(SPLIT_SETTING, bool(enabled))

    def watch(self, layer: QgsVectorLayer, layer_name: str) -> None:
        """Makes the links layer break what gets digitized into it."""
        if layer_name.lower() != "links":
            return

        layer_id = layer.id()
        if layer_id in self.watched:
            return

        self.watched.add(layer_id)
        layer.featureAdded.connect(partial(self.feature_added, layer_id))

    def layer_removed(self, layer_id: str) -> None:
        self.watched.discard(layer_id)

    def feature_added(self, layer_id: str, feature_id: int) -> None:
        """Queues the split for as soon as QGIS is done adding the feature.

        The digitizing tool still has its own edit command open at this point, and starting
        another one inside it nests them, which QGIS refuses. Letting the event loop turn once
        first also keeps the split on the undo stack as a step of its own.
        """
        if self.splitting or not self.enabled():
            return

        QTimer.singleShot(0, partial(self.split_feature, layer_id, feature_id))

    def split_feature(self, layer_id: str, feature_id: int) -> None:
        # PyQt turns an exception raised in a slot into qFatal(), which would take QGIS down with
        # the user's edits in it. A link left whole is a much better outcome than that.
        try:
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer is None or not layer.isEditable():
                return

            feature = layer.getFeature(feature_id)
            if not feature.isValid():
                return  # digitizing was undone before this got to run

            pieces = self.pieces_for(feature.geometry())
            if len(pieces) < 2:
                return

            self.replace_with_pieces(layer, feature, pieces)
        except Exception as error:
            self.qgis_project.message_log(
                QCoreApplication.translate("LinkSplitter", "Could not break the link at its nodes: {}").format(error),
                Qgis.MessageLevel.Warning,
            )

    def pieces_for(self, geometry: QgsGeometry) -> list:
        """The vertex runs the link should be broken into, or nothing if it stays whole."""
        vertices = line_vertices(geometry)
        if len(vertices) < 3:
            return []

        nodes = self.nodes_along(geometry)
        if not nodes:
            return []

        return split_at(vertices, nodes)

    def nodes_along(self, geometry: QgsGeometry) -> set:
        """Coordinates of every node inside the link's bounding box.

        One query for the whole link rather than one per vertex, since the spatial index is
        searched by frame anyway and a digitized link never covers much of the network.
        """
        project = self.qgis_project.project
        if project is None:
            return set()

        with project.db_connection as conn:
            nodes = conn.execute(
                "SELECT ST_X(geometry), ST_Y(geometry) FROM nodes WHERE ROWID IN "
                "(SELECT ROWID FROM SpatialIndex WHERE f_table_name = 'nodes' AND "
                "search_frame = GeomFromText(?, 4326))",
                (geometry.asWkt(),),
            ).fetchall()

        return {(x, y) for x, y in nodes}

    def replace_with_pieces(self, layer: QgsVectorLayer, feature: QgsFeature, pieces: list) -> None:
        """Shrinks the digitized link onto its first stretch and adds the rest alongside it.

        Keeping the original around for the first piece leaves its ids, and the attributes the
        form collected, exactly where QGIS put them.
        """
        multipart = QgsWkbTypes.isMultiType(layer.wkbType())
        extra = len(pieces) - 1
        ids = {field_name: next_ids(layer, field_name, extra) for field_name in ID_FIELDS}

        self.splitting = True
        layer.beginEditCommand(QCoreApplication.translate("LinkSplitter", "Break link at nodes"))
        try:
            layer.changeGeometry(feature.id(), line_geometry(pieces[0], multipart))

            for position, piece in enumerate(pieces[1:]):
                addition = QgsFeature(layer.fields())
                addition.setAttributes(feature.attributes())
                for field_name in ID_FIELDS:
                    set_if_present(addition, field_name, ids[field_name][position])
                addition.setGeometry(line_geometry(piece, multipart))
                layer.addFeature(addition)
        except Exception:
            layer.destroyEditCommand()
            raise
        else:
            layer.endEditCommand()
        finally:
            self.splitting = False


def line_vertices(geometry: QgsGeometry) -> list:
    """The vertices of a single line, or nothing for anything this has no business breaking."""
    if geometry is None or geometry.isEmpty():
        return []

    if not geometry.isMultipart():
        return geometry.asPolyline()

    parts = geometry.asMultiPolyline()
    return parts[0] if len(parts) == 1 else []


def split_at(vertices: list, break_points: set) -> list:
    """Cuts a vertex list at every interior vertex sitting on one of the break points.

    A vertex that repeats a break point it is already sitting on is passed over, since cutting
    there would only produce a link of no length.
    """
    pieces = []
    current = [vertices[0]]

    for vertex in vertices[1:-1]:
        current.append(vertex)
        if (vertex.x(), vertex.y()) not in break_points or has_no_length(current):
            continue

        pieces.append(current)
        current = [vertex]

    current.append(vertices[-1])
    pieces.append(current)

    return pieces


def has_no_length(vertices: list) -> bool:
    return len({(vertex.x(), vertex.y()) for vertex in vertices}) < 2


def line_geometry(vertices: list, multipart: bool) -> QgsGeometry:
    if multipart:
        return QgsGeometry.fromMultiPolylineXY([vertices])
    return QgsGeometry.fromPolylineXY(vertices)


def next_ids(layer: QgsVectorLayer, field_name: str, count: int) -> list:
    """The ids the pieces get, carrying on from the same maximum the layer's defaults use."""
    field_index = layer.fields().indexOf(field_name)
    if field_index < 0:
        return [None] * count

    largest = largest_value(layer, field_index)
    return [largest + position for position in range(1, count + 1)]


def largest_value(layer: QgsVectorLayer, field_index: int) -> int:
    """The largest id in the layer, counting the ones still sitting in the edit buffer.

    The link being split is itself one of those, so leaving the buffer out would hand its
    siblings the id it already took.
    """
    values = [layer.maximumValue(field_index)]

    buffer = layer.editBuffer()
    if buffer is not None:
        values += [feature.attribute(field_index) for feature in buffer.addedFeatures().values()]

    # The `maximum(...) + 1` the layer defaults to is a QGIS expression, and those count in
    # doubles, so the id the link being split is holding arrives here as a float
    numbers = [int(value) for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    return max(numbers) if numbers else 0


def set_if_present(feature: QgsFeature, field_name: str, value) -> None:
    if value is not None and feature.fields().indexOf(field_name) >= 0:
        feature[field_name] = value
