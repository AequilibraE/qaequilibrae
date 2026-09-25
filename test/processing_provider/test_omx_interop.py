import numpy as np
import openmatrix as omx
import pytest
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant

from qaequilibrae.modules.processing_provider.matrix_procedures.omx_interop import (
    OmxToTable,
    OmxZoneSlice,
    TableToOmx,
    read_omx_core,
)


def test_omx_table_round_trip(tmp_path):
    original = tmp_path / "original.omx"
    with omx.open_file(str(original), "w") as file:
        file.create_mapping("ids", [20, 10])
        file["cars"] = np.array([[1, 2], [3, 4]], dtype=float)
        file["trucks"] = np.array([[5, np.nan], [7, 8]], dtype=float)

    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()
    reader = OmxToTable()
    reader.initAlgorithm()
    result, ok = reader.run(
        {reader.PATH: str(original), reader.MAPPING: "ids", reader.OUTPUT: "memory:"}, context, feedback
    )
    assert ok, feedback.textLog()
    assert feedback.progress() == 100
    assert "Writing core: cars" in feedback.textLog()
    assert "OD table complete" in feedback.textLog()
    table = context.takeResultLayer(result[reader.OUTPUT])
    assert table.featureCount() == 8
    assert set(table.fields().names()) == {"origin", "destination", "core", "value"}

    writer = TableToOmx()
    writer.initAlgorithm()
    output = tmp_path / "roundtrip.omx"
    result, ok = writer.run({writer.INPUT: table, writer.OUTPUT: str(output)}, QgsProcessingContext(), feedback)
    assert ok, feedback.textLog()
    assert result[writer.OUTPUT] == str(output)
    assert feedback.progress() == 100
    assert "Reading and validating 8 OD rows" in feedback.textLog()
    assert "OMX file complete" in feedback.textLog()
    for core in ("cars", "trucks"):
        ids, values = read_omx_core(output, core)
        assert ids.tolist() == [10, 20]
        expected = np.array([[4, 3], [2, 1]]) if core == "cars" else np.array([[8, 7], [np.nan, 5]])
        np.testing.assert_allclose(values, expected)
    # Reading a core must not rewrite the source file.
    assert read_omx_core(original, "cars", "ids")[0].tolist() == [20, 10]


def test_omx_to_table_flushes_multiple_batches(tmp_path):
    path = tmp_path / "matrix.omx"
    zones = 65  # More than 4096 OD cells: one full batch and a partial batch.
    with omx.open_file(str(path), "w") as file:
        file.create_mapping("ids", list(range(zones)))
        file["cars"] = np.arange(zones * zones, dtype=float).reshape(zones, zones)

    action = OmxToTable()
    action.initAlgorithm()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()
    result, ok = action.run({action.PATH: str(path), action.OUTPUT: "memory:"}, context, feedback)
    assert ok, feedback.textLog()
    table = context.takeResultLayer(result[action.OUTPUT])
    assert table.featureCount() == zones * zones
    assert {(f["origin"], f["destination"]): f["value"] for f in table.getFeatures()} == {
        (origin, destination): float(origin * zones + destination)
        for origin in range(zones)
        for destination in range(zones)
    }


@pytest.mark.parametrize("direction,expected", [(0, {20: 1.0, 10: 2.0}), (1, {20: 1.0, 10: 3.0})])
def test_omx_zone_slice(tmp_path, direction, expected):
    path = tmp_path / "matrix.omx"
    with omx.open_file(str(path), "w") as file:
        file.create_mapping("ids", [20, 10])
        file["cars"] = np.array([[1, 2], [3, 4]], dtype=float)

    action = OmxZoneSlice()
    action.initAlgorithm()
    context = QgsProcessingContext()
    feedback = QgsProcessingFeedback()
    result, ok = action.run(
        {
            action.PATH: str(path),
            action.CORE: "cars",
            action.MAPPING: "ids",
            action.ZONE: 20,
            action.DIRECTION: direction,
            action.OUTPUT: "memory:",
        },
        context,
        feedback,
    )
    assert ok, feedback.textLog()
    assert feedback.progress() == 100
    assert "zone values to QGIS" in feedback.textLog()
    table = context.takeResultLayer(result[action.OUTPUT])
    assert table.featureCount() == 2
    assert {f["zone_id"]: f["data"] for f in table.getFeatures()} == expected


def test_table_to_omx_rejects_zone_ids_outside_omx_range(tmp_path):
    large_id = 2**53 + 1
    table = QgsVectorLayer("None", "od", "memory")
    table.dataProvider().addAttributes(
        [
            QgsField("origin", QVariant.LongLong),
            QgsField("destination", QVariant.LongLong),
            QgsField("core", QVariant.String),
            QgsField("value", QVariant.Double),
        ]
    )
    table.updateFields()
    for origin in (1, large_id):
        for destination in (1, large_id):
            feature = QgsFeature(table.fields())
            feature.setAttributes([origin, destination, "cars", 2.0])
            table.dataProvider().addFeatures([feature])

    writer = TableToOmx()
    writer.initAlgorithm()
    output = tmp_path / "large_ids.omx"
    with pytest.raises(QgsProcessingException, match="Zone IDs must fit in an OMX mapping"):
        writer.processAlgorithm(
            {writer.INPUT: table, writer.OUTPUT: str(output)}, QgsProcessingContext(), QgsProcessingFeedback()
        )
    assert not output.exists()


def test_table_to_omx_rejects_fractional_zone_ids(tmp_path):
    table = QgsVectorLayer("None", "od", "memory")
    table.dataProvider().addAttributes(
        [
            QgsField("origin", QVariant.Double),
            QgsField("destination", QVariant.Double),
            QgsField("core", QVariant.String),
            QgsField("value", QVariant.Double),
        ]
    )
    table.updateFields()
    feature = QgsFeature(table.fields())
    feature.setAttributes([1.5, 1.0, "cars", 2.0])
    table.dataProvider().addFeatures([feature])

    writer = TableToOmx()
    writer.initAlgorithm()
    with pytest.raises(QgsProcessingException, match="Invalid OD table row"):
        writer.processAlgorithm(
            {writer.INPUT: table, writer.OUTPUT: str(tmp_path / "fractional.omx")},
            QgsProcessingContext(),
            QgsProcessingFeedback(),
        )


def test_table_to_omx_cancel_removes_partial_file(tmp_path):
    table = QgsVectorLayer("None", "od", "memory")
    table.dataProvider().addAttributes(
        [
            QgsField("origin", QVariant.LongLong),
            QgsField("destination", QVariant.LongLong),
            QgsField("core", QVariant.String),
            QgsField("value", QVariant.Double),
        ]
    )
    table.updateFields()
    for origin in (1, 2):
        for destination in (1, 2):
            feature = QgsFeature(table.fields())
            feature.setAttributes([origin, destination, "cars", 1.0])
            table.dataProvider().addFeatures([feature])

    class CancelDuringWrite(QgsProcessingFeedback):
        def setProgress(self, progress):
            super().setProgress(progress)
            if progress >= 75:
                self.cancel()

    writer = TableToOmx()
    writer.initAlgorithm()
    path = tmp_path / "cancelled.omx"
    result = writer.processAlgorithm(
        {writer.INPUT: table, writer.OUTPUT: str(path)}, QgsProcessingContext(), CancelDuringWrite()
    )
    assert result == {}
    assert not path.exists()


def test_table_to_omx_rejects_incomplete_input(tmp_path):
    table = QgsVectorLayer("None", "od", "memory")
    table.dataProvider().addAttributes(
        [
            QgsField("origin", QVariant.LongLong),
            QgsField("destination", QVariant.LongLong),
            QgsField("core", QVariant.String),
            QgsField("value", QVariant.Double),
        ]
    )
    table.updateFields()
    for origin, destination in [(1, 1), (1, 2), (2, 1)]:
        feature = QgsFeature(table.fields())
        feature.setAttributes([origin, destination, "cars", 1.0])
        table.dataProvider().addFeatures([feature])
    writer = TableToOmx()
    writer.initAlgorithm()
    path = tmp_path / "incomplete.omx"
    with pytest.raises(QgsProcessingException, match="every origin-destination pair"):
        writer.processAlgorithm(
            {writer.INPUT: table, writer.OUTPUT: str(path)}, QgsProcessingContext(), QgsProcessingFeedback()
        )
    assert not path.exists()
