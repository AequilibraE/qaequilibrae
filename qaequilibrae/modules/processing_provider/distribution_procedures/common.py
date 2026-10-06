"""Inputs and output helpers for trip distribution."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import pandas as pd
from qgis.core import (
    NULL,
    Qgis,
    QgsProcessingException,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
)

from ..project_algorithm import ProjectAlgorithm

GRAVITY_FUNCTIONS = ["EXPO", "GAMMA", "POWER"]
CALIBRATION_FUNCTIONS = ["EXPO", "POWER"]


def add_trip_end_parameters(algorithm: ProjectAlgorithm) -> None:
    """Add the vector source and zone, production, and attraction fields."""
    algorithm.addParameter(QgsProcessingParameterFeatureSource("VECTOR_SOURCE", algorithm.tr("Trip-end vector layer")))
    for name, label in (
        ("INDEX_FIELD", "Index field (zone ID)"),
        ("ROW_FIELD", "Production field"),
        ("COLUMN_FIELD", "Attraction field"),
    ):
        algorithm.addParameter(
            QgsProcessingParameterField(
                name,
                algorithm.tr(label),
                parentLayerParameterName="VECTOR_SOURCE",
                type=Qgis.ProcessingFieldParameterDataType.Any
                if name == "INDEX_FIELD"
                else Qgis.ProcessingFieldParameterDataType.Numeric,
            )
        )


def vectors_from_source(source: Any, index_field: str, row_field: str, column_field: str) -> pd.DataFrame:
    """Read trip ends as floats, as required by AequilibraE."""
    field_names = [field.name() for field in source.fields()]
    if index_field not in field_names:
        raise QgsProcessingException(f"The vector layer has no field named '{index_field}'")

    rows = [[_clean_value(value) for value in feature.attributes()] for feature in source.getFeatures()]
    dataframe = pd.DataFrame(rows, columns=field_names).set_index(index_field)
    for field_name in (row_field, column_field):
        if field_name not in dataframe.columns:
            raise QgsProcessingException(f"The vector layer has no field named '{field_name}'")
        try:
            dataframe[field_name] = dataframe[field_name].astype(float)
        except (TypeError, ValueError) as error:
            raise QgsProcessingException(f"Field '{field_name}' cannot be read as a number: {error}") from error
    return dataframe


@contextmanager
def load_matrix_core(project: Any, matrix_name: str, core_name: str) -> Iterator[Any]:
    """Load one matrix core and close the matrix on every exit path."""
    if not core_name.strip():
        raise QgsProcessingException("A matrix core is required")
    matrix = project.matrices.get_matrix(matrix_name.strip())
    try:
        matrix.computational_view([core_name.strip()])
        yield matrix
    finally:
        matrix.close()


def push_report(feedback: Any, report: list[str] | dict[str, Any] | None) -> None:
    """Write an operation report to the Processing log."""
    if not report:
        return
    if isinstance(report, dict):
        report = [f"{key}: {value}" for key, value in report.items()]
    for line in report:
        feedback.pushInfo(str(line))


def _clean_value(value: Any) -> Any:
    """Turn QGIS nulls into pandas' missing value."""
    if value is None or value == NULL:
        return None
    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        return value
    return None if not hasattr(missing, "__len__") and missing else value
