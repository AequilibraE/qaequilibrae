"""Copy field values between layers using spatial matches."""

from collections.abc import Iterable, Sequence
from typing import Any, cast

from qgis.core import (
    Qgis,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSource,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsProcessingContext,
    QgsProcessingFeedback,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterString,
    QgsSpatialIndex,
    QgsWkbTypes,
)

from qaequilibrae.modules.processing_provider.project_algorithm import ProcessingAlgorithm

CLOSEST = "CLOSEST"
ENCLOSED = "ENCLOSED"
TOUCHING = "TOUCHING"
OPERATIONS = (CLOSEST, ENCLOSED, TOUCHING)


class SimpleTagError(ValueError):
    """An invalid spatial-tag configuration."""


def match_features(
    source_features: Sequence[QgsFeature],
    target_features: Sequence[QgsFeature],
    *,
    source_value_index: int,
    operation: str,
    source_match_index: int | None = None,
    target_match_index: int | None = None,
    source_is_polygon: bool = False,
    transform: QgsCoordinateTransform | None = None,
) -> dict[int, Any]:
    """Return source values for target features with a match.

    Unmatched features are omitted so the dialog can keep their current values.
    """
    if operation not in OPERATIONS:
        raise SimpleTagError(f"Unknown spatial-tag operation: {operation}")

    matching = source_match_index is not None and target_match_index is not None
    index = QgsSpatialIndex()
    source_geometry: dict[int, QgsGeometry] = {}
    source_value: dict[int, Any] = {}
    source_match: dict[int, Any] = {}
    for feature in source_features:
        geometry = feature.geometry()
        if geometry is None or geometry.isEmpty():
            continue
        index.addFeature(feature)
        source_geometry[feature.id()] = geometry
        source_value[feature.id()] = feature.attributes()[source_value_index]
        if matching:
            source_match[feature.id()] = feature.attributes()[source_match_index]

    matches: dict[int, Any] = {}
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
            geometry,
            operation,
            source_is_polygon,
            feature.attributes()[target_match_index] if matching else None,
        )
        if value is not None:
            matches[feature.id()] = value
    return matches


def _match_feature(
    index: QgsSpatialIndex,
    source_geometry: dict[int, QgsGeometry],
    source_value: dict[int, Any],
    source_match: dict[int, Any],
    geometry: QgsGeometry,
    operation: str,
    source_is_polygon: bool,
    target_match_value: Any,
) -> Any | None:
    """Choose the source value for one target geometry."""
    if operation == CLOSEST:
        # Rank five indexed neighbours by real distance, not bounding-box distance.
        candidates = index.nearestNeighbor(geometry.centroid().asPoint(), 5)
        candidates.sort(key=lambda candidate: source_geometry[candidate].distance(geometry))
    else:
        candidates = index.intersects(geometry.boundingBox())
    if source_match:
        candidates = [candidate for candidate in candidates if source_match[candidate] == target_match_value]

    if operation == CLOSEST:
        return source_value[candidates[0]] if candidates else None

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
    best_value: Any | None = None
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


class SimpleTag(ProcessingAlgorithm):
    """Copy a source field into a target layer using a spatial relationship."""

    algorithm_name = "simple_tag"
    display_name = "Simple tag"
    group_name = "Mapping"
    group_id = "mapping"

    SOURCE = "SOURCE"
    SOURCE_FIELD = "SOURCE_FIELD"
    TARGET = "TARGET"
    TARGET_FIELD = "TARGET_FIELD"
    OPERATION = "OPERATION"
    MATCH_SOURCE_FIELD = "MATCH_SOURCE_FIELD"
    MATCH_TARGET_FIELD = "MATCH_TARGET_FIELD"
    OUTPUT = "OUTPUT"

    OPERATION_LABELS = ("Closest", "Enclosed", "Touching")

    def initAlgorithm(self, configuration: dict[str, Any] | None = None) -> None:
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.SOURCE, self.tr("Source layer"), types=[Qgis.ProcessingSourceType.VectorAnyGeometry]
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.SOURCE_FIELD, self.tr("Source field (values to copy)"), parentLayerParameterName=self.SOURCE
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.TARGET, self.tr("Target layer"), types=[Qgis.ProcessingSourceType.VectorAnyGeometry]
            )
        )
        self.addParameter(
            QgsProcessingParameterString(self.TARGET_FIELD, self.tr("Target field name"), defaultValue="tagged")
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
                self.OUTPUT, self.tr("Tagged layer"), type=Qgis.ProcessingSourceType.VectorAnyGeometry
            )
        )

    def processAlgorithm(
        self, parameters: dict[str, Any], context: QgsProcessingContext, feedback: QgsProcessingFeedback | None
    ) -> dict[str, Any]:
        # GUI adapters use original feature IDs to apply only matched values in place.
        self.matches: dict[int, Any] = {}
        if feedback is None:
            feedback = QgsProcessingFeedback()
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
        if bool(source_match_field) != bool(target_match_field):
            raise QgsProcessingException(self.tr("Select both match fields, or leave both empty"))
        source_match_index = source.fields().lookupField(source_match_field) if source_match_field else None
        target_match_index = target.fields().lookupField(target_match_field) if target_match_field else None
        if source_match_field and (source_match_index is None or source_match_index < 0):
            raise QgsProcessingException(self.tr(f"The source match field '{source_match_field}' does not exist"))
        if target_match_field and (target_match_index is None or target_match_index < 0):
            raise QgsProcessingException(self.tr(f"The target match field '{target_match_field}' does not exist"))

        feedback.pushInfo(self.tr("Reading source and target features"))
        source_features = list(cast(Iterable[QgsFeature], source.getFeatures()))
        target_features = list(cast(Iterable[QgsFeature], target.getFeatures()))
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

        self.matches = matches
        fields = QgsFields()
        for field in target.fields():
            fields.append(field)
        if fields.lookupField(target_field) < 0:
            source_type = source.fields().field(source_field).type()
            fields.append(QgsField(target_field, source_type))
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
            if not sink.addFeature(output):
                raise QgsProcessingException(self.tr("Could not write a tagged feature to the output"))
            feedback.setProgress(index * 100 / max(len(target_features), 1))

        feedback.pushInfo(self.tr(f"Tagged {len(matches)} of {len(target_features)} features"))
        return {self.OUTPUT: destination}

    @staticmethod
    def _transform(
        source: QgsFeatureSource, target: QgsFeatureSource, context: QgsProcessingContext
    ) -> QgsCoordinateTransform | None:
        source_crs = source.sourceCrs()
        target_crs = target.sourceCrs()
        if not source_crs.isValid() or not target_crs.isValid() or source_crs == target_crs:
            return None
        return QgsCoordinateTransform(target_crs, source_crs, context.transformContext())

    def shortHelpString(self) -> str:
        return self.tr(
            "Copies a source field value to a new output copy of the target layer. Closest selects "
            "the nearest of five indexed source candidates. Enclosed selects the first containing "
            "feature. Touching selects the feature with the greatest shared length, or area when "
            "both layers are polygons. Optional match fields must be supplied as a pair. Target "
            "geometries are transformed to the source CRS for matching. Targets without a match "
            "have a null output value."
        )

    def tags(self) -> list[str]:
        return ["spatial", "join", "tag", "mapping"]
