"""Export filtered transit supply metrics as a Processing table."""

from typing import Any

import pandas as pd
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from qaequilibrae.modules.processing_provider.project import borrow_project
from qaequilibrae.modules.processing_provider.project_algorithm import ProjectAlgorithm
from qaequilibrae.modules.transit_procedures.transit_supply_metrics import SupplyMetrics


class TransitSupplyMetricsAlgorithm(ProjectAlgorithm):
    """Compute route, pattern, stop, or zone transit supply metrics."""

    algorithm_name = "transitSupplyMetrics"
    display_name = "Transit supply metrics"
    group_name = "Transit"
    group_id = "transit"

    ENTITY = "ENTITY"
    FROM_MINUTE = "FROM_MINUTE"
    TO_MINUTE = "TO_MINUTE"
    ROUTES = "ROUTES"
    PATTERNS = "PATTERNS"
    STOPS = "STOPS"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, configuration: dict | None = None) -> None:
        self.add_project_folder_parameter()
        self.addParameter(
            QgsProcessingParameterEnum(
                self.ENTITY,
                self.tr("Metrics for"),
                options=[self.tr("Routes"), self.tr("Patterns"), self.tr("Stops"), self.tr("Zones")],
                usesStaticStrings=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.FROM_MINUTE,
                self.tr("Start time (minutes after midnight)"),
                type=Qgis.ProcessingNumberParameterType.Integer,
                minValue=0,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.TO_MINUTE,
                self.tr("End time (minutes after midnight)"),
                type=Qgis.ProcessingNumberParameterType.Integer,
                minValue=0,
                optional=True,
            )
        )
        for key, label in (
            (self.ROUTES, "Route IDs (comma-separated, optional)"),
            (self.PATTERNS, "Pattern IDs (comma-separated, optional)"),
            (self.STOPS, "Stop IDs (comma-separated, optional)"),
        ):
            self.addParameter(QgsProcessingParameterString(key, self.tr(label), optional=True))
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr("Transit supply metrics table"),
                type=Qgis.ProcessingSourceType.Vector,
            )
        )

    def processAlgorithm(
        self,
        parameters: dict,
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict:
        folder = self.project_folder(parameters, context)
        if not folder:
            raise QgsProcessingException(self.tr("An AequilibraE project folder is required."))
        entity_index = self.parameterAsEnum(parameters, self.ENTITY, context)
        metric_names = ("route_metrics", "pattern_metrics", "stop_metrics", "zone_metrics")
        if entity_index not in range(len(metric_names)):
            raise QgsProcessingException(self.tr("Select a valid transit entity."))

        def read_filter(key: str) -> list[int] | None:
            text = self.parameterAsString(parameters, key, context).strip()
            if not text:
                return None
            try:
                values = [int(value.strip()) for value in text.split(",")]
            except ValueError as error:
                raise QgsProcessingException(self.tr(f"{key} must contain comma-separated integer IDs.")) from error
            if len(set(values)) != len(values):
                raise QgsProcessingException(self.tr(f"{key} contains duplicate IDs."))
            return values

        from_minute = (
            self.parameterAsInt(parameters, self.FROM_MINUTE, context)
            if parameters.get(self.FROM_MINUTE) is not None
            else None
        )
        to_minute = (
            self.parameterAsInt(parameters, self.TO_MINUTE, context)
            if parameters.get(self.TO_MINUTE) is not None
            else None
        )
        if from_minute is not None and to_minute is not None and from_minute > to_minute:
            raise QgsProcessingException(self.tr("Start time must be before end time."))
        filters = {
            "routes": read_filter(self.ROUTES),
            "patterns": read_filter(self.PATTERNS),
            "stops": read_filter(self.STOPS),
            "from_minute": from_minute,
            "to_minute": to_minute,
        }

        try:
            with borrow_project(folder) as project:
                if feedback and feedback.isCanceled():
                    return {}
                supply_metrics = SupplyMetrics(project)
                methods = {
                    "route_metrics": supply_metrics.route_metrics,
                    "pattern_metrics": supply_metrics.pattern_metrics,
                    "stop_metrics": supply_metrics.stop_metrics,
                    "zone_metrics": supply_metrics.zone_metrics,
                }
                metrics = methods[metric_names[entity_index]](**filters)
                metrics = metrics.reset_index(drop=True)
                fields = self._fields(metrics)
                sink, destination = self.parameterAsSink(
                    parameters, self.OUTPUT, context, fields, Qgis.WkbType.NoGeometry, QgsCoordinateReferenceSystem()
                )
                if sink is None:
                    raise QgsProcessingException(self.tr("Could not create the metrics output table."))
                for row in metrics.itertuples(index=False, name=None):
                    if feedback and feedback.isCanceled():
                        return {}
                    feature = QgsFeature(fields)
                    feature.setAttributes([self._value(value) for value in row])
                    if not sink.addFeature(feature):
                        raise QgsProcessingException(self.tr("Could not write a metrics table row."))
                return {self.OUTPUT: destination}
        except (KeyError, ValueError, OSError) as error:
            raise QgsProcessingException(str(error)) from error

    @staticmethod
    def _fields(dataframe: pd.DataFrame) -> QgsFields:
        fields = QgsFields()
        for name, dtype in dataframe.dtypes.items():
            if pd.api.types.is_bool_dtype(dtype):
                variant_type = QVariant.Bool
            elif pd.api.types.is_integer_dtype(dtype):
                variant_type = QVariant.LongLong
            elif pd.api.types.is_numeric_dtype(dtype):
                variant_type = QVariant.Double
            else:
                variant_type = QVariant.String
            fields.append(QgsField(str(name), variant_type))
        return fields

    @staticmethod
    def _value(value: Any) -> Any:
        if pd.isna(value):
            return None
        return value.item() if hasattr(value, "item") else value
