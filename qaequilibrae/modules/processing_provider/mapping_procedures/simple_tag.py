"""Spatial-tag operation and its QGIS Processing adapter.

The matching operation receives plain QGIS features and returns the value every
target feature should receive. The :class:`SimpleTag` adapter translates QGIS
Processing inputs and outputs around it, and the desktop dialog uses the same
operation so both entry points stay in step.
"""

from typing import Any

from qgis.core import (
    Qgis,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterString,
    QgsSpatialIndex,
    QgsWkbTypes,
)

from qaequilibrae.i18n.translate import trlt

CLOSEST = "CLOSEST"
ENCLOSED = "ENCLOSED"
TOUCHING = "TOUCHING"
OPERATIONS = (CLOSEST, ENCLOSED, TOUCHING)


class SimpleTagError(ValueError):
    """An invalid spatial-tag configuration."""


def match_features(
    source_features,
    target_features,
    *,
    source_value_index: int,
    operation: str,
    source_match_index: int | None = None,
    target_match_index: int | None = None,
    source_is_polygon: bool = False,
    transform: QgsCoordinateTransform | None = None,
) -> dict[int, Any]:
    """Return the value each target feature should receive.

    ``source_features`` and ``target_features`` are QGIS features. A target
    feature is only present in the result when the operation found a source it
    can match, which is how the dialog decides to leave an existing value alone.
    """
    if operation not in OPERATIONS:
        raise SimpleTagError(f"Unknown spatial-tag operation: {operation}")

    matching = source_match_index is not None and target_match_index is not None
    index = QgsSpatialIndex()
    source_geometry = {}
    source_value = {}
    source_match = {}
    for feature in source_features:
        index.addFeature(feature)
        source_geometry[feature.id()] = feature.geometry()
        source_value[feature.id()] = feature.attributes()[source_value_index]
        if matching:
            source_match[feature.id()] = feature.attributes()[source_match_index]

    target_match = {}
    if matching:
        for feature in target_features:
            target_match[feature.id()] = feature.attributes()[target_match_index]

    matches = {}
    for feature in target_features:
        geometry = feature.geometry()
        if geometry is None or geometry.isEmpty():
            continue
        if transform is not None:
            geometry = QgsGeometry(geometry)
            geometry.transform(transform)

        value = _match_feature(
            index,
            source_geometry,
            source_value,
            source_match,
            feature.id(),
            geometry,
            operation,
            source_is_polygon,
            target_match.get(feature.id()),
        )
        if value is not None:
            matches[feature.id()] = value
    return matches


def _match_feature(
    index,
    source_geometry,
    source_value,
    source_match,
    target_id,
    geometry,
    operation,
    source_is_polygon,
    target_match_value,
):
    """Choose the source value for one target geometry."""
    if operation in (ENCLOSED, TOUCHING):
        return _enclosed_or_touching(
            index,
            source_geometry,
            source_value,
            source_match,
            geometry,
            operation,
            source_is_polygon,
            target_match_value,
        )
    return _closest(index, source_geometry, source_value, source_match, geometry, target_match_value)


def _enclosed_or_touching(
    index, source_geometry, source_value, source_match, geometry, operation, source_is_polygon, target_match_value
):
    candidates = index.intersects(geometry.boundingBox())
    if source_match:
        candidates = [candidate for candidate in candidates if source_match[candidate] == target_match_value]

    if operation == ENCLOSED:
        # Either the source sits inside the target or the target sits inside the source.
        for candidate in candidates:
            if source_is_polygon and source_geometry[candidate].contains(geometry):
                return source_value[candidate]
            if not source_is_polygon and geometry.contains(source_geometry[candidate]):
                return source_value[candidate]
        return None

    # TOUCHING keeps the match with the largest shared length, or area for two polygons.
    use_area = source_is_polygon and QgsWkbTypes.geometryType(geometry.wkbType()) == Qgis.GeometryType.Polygon
    best_value = None
    best_measure = -1.0
    for candidate in candidates:
        intersection = source_geometry[candidate].intersection(geometry)
        if intersection is None or intersection.isEmpty():
            continue
        measure = intersection.area() if use_area else intersection.length()
        if measure > best_measure and measure > 0:
            best_measure = measure
            best_value = source_value[candidate]
    return best_value


def _closest(index, source_geometry, source_value, source_match, geometry, target_match_value):
    # A spatial index alone cannot rank the true nearest feature, so a handful of
    # neighbours are compared by real distance before one is chosen.
    candidates = index.nearestNeighbor(geometry.centroid().asPoint(), 5)
    ordered = sorted(candidates, key=lambda candidate: source_geometry[candidate].distance(geometry))
    for candidate in ordered:
        if not source_match or source_match[candidate] == target_match_value:
            return source_value[candidate]
    return None


class SimpleTag(QgsProcessingAlgorithm):
    """Copy a source field into a target layer using a spatial relationship."""

    SOURCE = "SOURCE"
    SOURCE_FIELD = "SOURCE_FIELD"
    TARGET = "TARGET"
    TARGET_FIELD = "TARGET_FIELD"
    OPERATION = "OPERATION"
    MATCH_SOURCE_FIELD = "MATCH_SOURCE_FIELD"
    MATCH_TARGET_FIELD = "MATCH_TARGET_FIELD"
    OUTPUT = "OUTPUT"

    OPERATION_LABELS = ("Closest", "Enclosed", "Touching")

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.SOURCE,
                self.tr("Source layer"),
                types=[Qgis.ProcessingSourceType.VectorAnyGeometry],
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.SOURCE_FIELD,
                self.tr("Source field (values to copy)"),
                parentLayerParameterName=self.SOURCE,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.TARGET,
                self.tr("Target layer"),
                types=[Qgis.ProcessingSourceType.VectorAnyGeometry],
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.TARGET_FIELD,
                self.tr("Target field name"),
                defaultValue="tagged",
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.OPERATION,
                self.tr("Operation"),
                options=[self.tr(label) for label in self.OPERATION_LABELS],
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.MATCH_SOURCE_FIELD,
                self.tr("Source field to match (optional)"),
                parentLayerParameterName=self.SOURCE,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.MATCH_TARGET_FIELD,
                self.tr("Target field to match (optional)"),
                parentLayerParameterName=self.TARGET,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Tagged layer"),
                type=Qgis.ProcessingSourceType.VectorAnyGeometry,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.SOURCE, context)
        target = self.parameterAsSource(parameters, self.TARGET, context)
        if source is None or target is None:
            raise QgsProcessingException(self.tr("Both a source and a target layer are required"))

        source_field = self.parameterAsString(parameters, self.SOURCE_FIELD, context)
        target_field = self.parameterAsString(parameters, self.TARGET_FIELD, context) or source_field
        operation = OPERATIONS[self.parameterAsEnum(parameters, self.OPERATION, context)]
        source_match_field = self.parameterAsString(parameters, self.MATCH_SOURCE_FIELD, context) or None
        target_match_field = self.parameterAsString(parameters, self.MATCH_TARGET_FIELD, context) or None

        source_value_index = source.fields().lookupField(source_field)
        if source_value_index < 0:
            raise QgsProcessingException(self.tr(f"The source field '{source_field}' does not exist"))
        source_match_index = source.fields().lookupField(source_match_field) if source_match_field else None
        target_match_index = target.fields().lookupField(target_match_field) if target_match_field else None

        feedback.pushInfo(self.tr("Reading source and target features"))
        source_features = list(source.getFeatures())
        target_features = list(target.getFeatures())
        if feedback.isCanceled():
            return {}

        transform = self._transform(source, target, context)
        try:
            matches = match_features(
                source_features,
                target_features,
                source_value_index=source_value_index,
                operation=operation,
                source_match_index=source_match_index,
                target_match_index=target_match_index,
                source_is_polygon=QgsWkbTypes.geometryType(source.wkbType()) == Qgis.GeometryType.Polygon,
                transform=transform,
            )
        except SimpleTagError as error:
            raise QgsProcessingException(self.tr(str(error))) from error

        fields = self._output_fields(source, target, source_field, target_field)
        sink, destination = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            target.wkbType(),
            target.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        tagged_index = fields.lookupField(target_field)
        target_field_count = target.fields().count()
        for index, feature in enumerate(target_features, start=1):
            if feedback.isCanceled():
                return {}
            output = QgsFeature(fields)
            output.setGeometry(feature.geometry())
            values = list(feature.attributes())
            value = matches.get(feature.id())
            if tagged_index < target_field_count:
                values[tagged_index] = value
            else:
                values.append(value)
            output.setAttributes(values)
            sink.addFeature(output)
            feedback.setProgress(index * 100 / max(len(target_features), 1))

        feedback.pushInfo(self.tr(f"Tagged {len(matches)} of {len(target_features)} features"))
        return {self.OUTPUT: destination}

    @staticmethod
    def _transform(source, target, context):
        source_crs = source.sourceCrs()
        target_crs = target.sourceCrs()
        if not source_crs.isValid() or not target_crs.isValid() or source_crs == target_crs:
            return None
        return QgsCoordinateTransform(target_crs, source_crs, context.transformContext())

    @staticmethod
    def _output_fields(source, target, source_field, target_field):
        fields = QgsFields()
        for field in target.fields():
            fields.append(field)
        if fields.lookupField(target_field) < 0:
            source_type = source.fields().field(source_field).type()
            fields.append(QgsField(target_field, source_type))
        return fields

    def name(self):
        return "simple_tag"

    def displayName(self):
        return self.tr("Simple tag")

    def group(self):
        return self.tr("Mapping")

    def groupId(self):
        return "mapping"

    def shortHelpString(self):
        return self.tr(
            "Copies values from a source field into a target layer using a spatial relationship. "
            "Use Enclosed, Touching or Closest to decide which source feature wins."
        )

    def createInstance(self):
        return SimpleTag()

    def tags(self):
        return ["spatial", "join", "tag", "mapping"]

    def tr(self, message):
        return trlt("SimpleTag", message)
