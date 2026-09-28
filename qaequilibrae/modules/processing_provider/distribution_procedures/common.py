"""Shared helpers for the trip-distribution Processing algorithms."""

from __future__ import annotations

from typing import Any

import pandas as pd
from qgis.core import NULL, QgsProcessingException

# The synthetic gravity model only understands these functional forms.
GRAVITY_FUNCTIONS = ["EXPO", "GAMMA", "POWER"]
# Calibration only has a closed-form update for these two forms.
CALIBRATION_FUNCTIONS = ["EXPO", "POWER"]


class DistributionError(ValueError):
    """An input or computation error that callers can present in their own way."""


def dataframe_from_source(source: Any, index_field: str) -> pd.DataFrame:
    """Read a feature source into a DataFrame indexed by *index_field*.

    Distribution vectors are matched to matrix zones by their index, so the
    chosen index field moves out of the columns and into the index.
    """
    field_names = [field.name() for field in source.fields()]
    if index_field not in field_names:
        raise QgsProcessingException(f"The vector layer has no field named '{index_field}'")

    rows = [[_clean_value(value) for value in feature.attributes()] for feature in source.getFeatures()]
    return pd.DataFrame(rows, columns=field_names).set_index(index_field)


def vectors_from_source(source: Any, index_field: str, row_field: str, column_field: str) -> pd.DataFrame:
    """Build the trip-end vectors a distribution procedure expects.

    The row and column totals are cast to float because AequilibraE rejects
    integer totals, while QGIS layers are free to store them as integers.
    """
    dataframe = dataframe_from_source(source, index_field)
    for field_name in (row_field, column_field):
        if field_name not in dataframe.columns:
            raise QgsProcessingException(f"The vector layer has no field named '{field_name}'")
        try:
            dataframe[field_name] = dataframe[field_name].astype(float)
        except (TypeError, ValueError) as error:
            raise QgsProcessingException(f"Field '{field_name}' cannot be read as a number: {error}") from error
    return dataframe


def load_matrix_core(project: Any, matrix_name: str, core_name: str) -> Any:
    """Load a project matrix and set its computational view to a single core."""
    matrix_name = matrix_name.strip()
    core_name = core_name.strip()
    if not matrix_name:
        raise QgsProcessingException("A matrix name is required")
    if not core_name:
        raise QgsProcessingException("A matrix core is required")

    available = project.matrices.list()
    if matrix_name not in available["name"].tolist():
        raise QgsProcessingException(f"The project has no matrix named '{matrix_name}'")

    matrix = project.matrices.get_matrix(matrix_name)
    if core_name not in matrix.names:
        cores = ", ".join(matrix.names)
        raise QgsProcessingException(f"Matrix '{matrix_name}' has no core named '{core_name}'. Available: {cores}")
    matrix.computational_view([core_name])
    return matrix


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
