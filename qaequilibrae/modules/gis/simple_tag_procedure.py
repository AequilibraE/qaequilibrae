from aequilibrae.utils.interface.worker_thread import WorkerThread
from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject

from qaequilibrae.modules.common_tools import get_vector_layer_by_name
from qaequilibrae.modules.common_tools.global_parameters import multi_line, multi_point, line_types, point_types
from qaequilibrae.modules.processing_provider.mapping_procedures.simple_tag import match_features


class SimpleTAG(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, flayer, tlayer, ffield, tfield, fmatch, tmatch, operation, geo_types):
        WorkerThread.__init__(self, parentThread)
        self.ffield = ffield
        self.tfield = tfield
        self.fmatch = fmatch
        self.tmatch = tmatch
        self.operation = operation
        self.geo_types = geo_types
        self.transform = None
        self.error = None
        self.from_layer = get_vector_layer_by_name(flayer)
        self.to_layer = get_vector_layer_by_name(tlayer)

        # Layer types
        if self.from_layer.wkbType() in point_types + multi_point:
            self.ftype = "point"
        elif self.from_layer.wkbType() in line_types + multi_line:
            self.ftype = "line"
        else:
            self.ftype = "area"

        if self.to_layer.wkbType() in point_types + multi_point:
            self.ttype = "point"
        elif self.to_layer.wkbType() in line_types + multi_line:
            self.ttype = "line"
        else:
            self.ttype = "area"

        self.all_attr = {}

    def doWork(self):
        self.signal.emit(["set_text", self.tr("Initializing. Sit tight")])

        to_layer_counts = self.to_layer.dataProvider().featureCount()
        from_layer_counts = self.from_layer.dataProvider().featureCount()

        self.transform = self._coordinate_transform()

        # FIELDS INDICES
        idx = self.from_layer.dataProvider().fieldNameIndex(self.ffield)
        fid = self.to_layer.dataProvider().fieldNameIndex(self.tfield)
        source_match_index = self.from_layer.dataProvider().fieldNameIndex(self.fmatch) if self.fmatch else None
        target_match_index = self.to_layer.dataProvider().fieldNameIndex(self.tmatch) if self.tmatch else None
        invalid_fields = []
        if idx < 0:
            invalid_fields.append(f"source value field '{self.ffield}'")
        if fid < 0:
            invalid_fields.append(f"target field '{self.tfield}'")
        if source_match_index is not None and source_match_index < 0:
            invalid_fields.append(f"source match field '{self.fmatch}'")
        if target_match_index is not None and target_match_index < 0:
            invalid_fields.append(f"target match field '{self.tmatch}'")
        if invalid_fields:
            self.error = "The following fields do not exist: " + ", ".join(invalid_fields)
            self.signal.emit(["finished"])
            return

        self.signal.emit(["start", from_layer_counts, self.tr("Reading source layer")])
        source_features = list(self.from_layer.getFeatures())
        if self.fmatch:
            self.from_match = {feature.id(): feature.attributes()[source_match_index] for feature in source_features}

        target_features = list(self.to_layer.getFeatures())

        self.signal.emit(["start", to_layer_counts, self.tr("Performing spatial matching")])
        self.all_attr = match_features(
            source_features,
            target_features,
            source_value_index=idx,
            operation=self.operation,
            source_match_index=source_match_index,
            target_match_index=target_match_index,
            source_is_polygon=self.ftype == "area",
            transform=self.transform,
        )

        self.signal.emit(["start", to_layer_counts, self.tr("Writing data to target layer")])
        for i, feat in enumerate(self.to_layer.getFeatures()):
            self.signal.emit(["update", i + 1, f"Writing data to target layer: {i}"])
            if self.all_attr.get(feat.id()) is not None:
                _ = self.to_layer.dataProvider().changeAttributeValues({feat.id(): {fid: self.all_attr[feat.id()]}})

        self.to_layer.commitChanges()
        self.to_layer.updateFields()

        self.signal.emit(["finished"])

    def _coordinate_transform(self):
        """Transform target geometries into the source CRS before matching."""
        source_crs = QgsCoordinateReferenceSystem(f"EPSG:{int(self.from_layer.crs().authid().split(':')[1])}")
        target_crs = QgsCoordinateReferenceSystem(f"EPSG:{int(self.to_layer.crs().authid().split(':')[1])}")
        if source_crs != target_crs:
            return QgsCoordinateTransform(target_crs, source_crs, QgsProject.instance())
        return None
