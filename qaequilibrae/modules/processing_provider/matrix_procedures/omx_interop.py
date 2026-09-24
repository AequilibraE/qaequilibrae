"""Convert OMX cores to and from non-spatial QGIS OD tables."""

from pathlib import Path

import numpy as np
import openmatrix as omx
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterString,
    QgsWkbTypes,
)

from qaequilibrae.i18n.translate import trlt
from qaequilibrae.qgis_logging import get_logger, with_processing_feedback

logger = get_logger(__name__)


# A long-form table avoids QGIS field-count limits for large matrices. Each row
# represents one cell; a core column keeps multi-core OMX files reversible.
FIELDS = QgsFields()
for field in (
    QgsField("origin", QVariant.LongLong),
    QgsField("destination", QVariant.LongLong),
    QgsField("core", QVariant.String),
    QgsField("value", QVariant.Double),
):
    FIELDS.append(field)


def read_omx_core(path, core, mapping=None):
    """Return zone IDs and values for one core, without modifying the OMX file."""
    with omx.open_file(str(path), "r") as file:
        if core not in file.list_matrices():
            raise ValueError(f"OMX core not found: {core}")
        mappings = file.list_mappings()
        if mapping is None:
            if not mappings:
                raise ValueError("OMX file has no zone mapping")
            mapping = mappings[0]
        if mapping not in mappings:
            raise ValueError(f"OMX mapping not found: {mapping}")
        ids = np.asarray(list(file.mapping(mapping).keys()))
        values = np.asarray(file[core][:])
        if values.shape != (len(ids), len(ids)):
            raise ValueError(f"Core {core} does not match mapping {mapping}")
        return ids, values


class OmxToTable(QgsProcessingAlgorithm):
    PATH = "omx_path"
    MAPPING = "mapping"
    OUTPUT = "output"

    def initAlgorithm(self, configuration=None):
        self.addParameter(QgsProcessingParameterFile(self.PATH, self.tr("OMX file"), fileFilter="OpenMatrix (*.omx)"))
        self.addParameter(
            QgsProcessingParameterString(self.MAPPING, self.tr("Zone mapping (blank: first mapping)"), optional=True)
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(self.OUTPUT, self.tr("OD table"), type=Qgis.ProcessingSourceType.Vector)
        )

    @with_processing_feedback
    def processAlgorithm(self, parameters, context, feedback):
        path = self.parameterAsFile(parameters, self.PATH, context)
        mapping = self.parameterAsString(parameters, self.MAPPING, context) or None
        logger.info(self.tr("Opening OMX file: {}").format(path))
        feedback.setProgress(0)
        try:
            with omx.open_file(path, "r") as file:
                cores = file.list_matrices()
                mappings = file.list_mappings()
                chosen = mapping or (mappings[0] if mappings else None)
                if chosen not in mappings:
                    raise ValueError(f"OMX mapping not found: {chosen}")
                ids = list(file.mapping(chosen).keys())
                if len(set(ids)) != len(ids) or any(not isinstance(i, (int, np.integer)) for i in ids):
                    raise ValueError("Zone mapping must contain unique integer IDs")
                total = len(cores) * len(ids)
                logger.info(
                    self.tr("Writing {} cores and {} zones ({} OD cells) to QGIS").format(
                        len(cores), len(ids), total * len(ids)
                    )
                )
                sink, destination = self.parameterAsSink(
                    parameters, self.OUTPUT, context, FIELDS, QgsWkbTypes.NoGeometry, QgsCoordinateReferenceSystem()
                )
                if sink is None:
                    raise QgsProcessingException(self.tr("Could not create OD table"))
                progress_step = max(1, total // 100)
                for core_number, core in enumerate(cores):
                    logger.info(self.tr("Writing core: {}").format(core))
                    values = file[core]
                    if values.shape != (len(ids), len(ids)):
                        raise ValueError(f"Core {core} does not match mapping {chosen}")
                    for row, origin in enumerate(ids):
                        if feedback.isCanceled():
                            del sink
                            return {}
                        for column, destination_id in enumerate(ids):
                            feature = QgsFeature()
                            feature.setAttributes([int(origin), int(destination_id), core, float(values[row, column])])
                            if not sink.addFeature(feature):
                                raise QgsProcessingException(self.tr("Could not write OD table row"))
                        completed = core_number * len(ids) + row + 1
                        if completed % progress_step == 0 or completed == total:
                            feedback.setProgress(99 * completed / total)
                del sink
                feedback.setProgress(100)
                logger.info(self.tr("OD table complete"))
                return {self.OUTPUT: destination}
        except (OSError, ValueError, KeyError) as error:
            raise QgsProcessingException(str(error)) from error

    def name(self):
        return "omxtotable"

    def displayName(self):
        return self.tr("OMX to QGIS OD table")

    def group(self):
        return self.tr("Data")

    def groupId(self):
        return "data"

    def shortHelpString(self):
        return self.tr(
            "Reads every OMX core into a non-spatial table with origin, destination, core and value fields. Select a mapping if the file has more than one."
        )

    def createInstance(self):
        return OmxToTable()

    def tr(self, message):
        return trlt("OmxToTable", message)


class OmxZoneSlice(QgsProcessingAlgorithm):
    """Expose one origin or destination as a small table for a zone-layer join."""

    PATH = "omx_path"
    CORE = "core"
    MAPPING = "mapping"
    ZONE = "zone_id"
    DIRECTION = "direction"
    OUTPUT = "output"

    def initAlgorithm(self, configuration=None):
        self.addParameter(QgsProcessingParameterFile(self.PATH, self.tr("OMX file"), fileFilter="OpenMatrix (*.omx)"))
        self.addParameter(QgsProcessingParameterString(self.CORE, self.tr("Matrix core")))
        self.addParameter(
            QgsProcessingParameterString(self.MAPPING, self.tr("Zone mapping (blank: first mapping)"), optional=True)
        )
        self.addParameter(
            QgsProcessingParameterNumber(
                self.ZONE, self.tr("Origin or destination zone ID"), type=Qgis.ProcessingNumberParameterType.Integer
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.DIRECTION, self.tr("Slice"), options=[self.tr("By origin"), self.tr("By destination")]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT, self.tr("Zone values"), type=Qgis.ProcessingSourceType.Vector
            )
        )

    @with_processing_feedback
    def processAlgorithm(self, parameters, context, feedback):
        path = self.parameterAsFile(parameters, self.PATH, context)
        core = self.parameterAsString(parameters, self.CORE, context)
        mapping = self.parameterAsString(parameters, self.MAPPING, context) or None
        zone = self.parameterAsInt(parameters, self.ZONE, context)
        direction = self.parameterAsEnum(parameters, self.DIRECTION, context)
        logger.info(self.tr("Opening OMX file: {}").format(path))
        feedback.setProgress(0)
        try:
            with omx.open_file(path, "r") as file:
                if core not in file.list_matrices():
                    raise ValueError(f"OMX core not found: {core}")
                mappings = file.list_mappings()
                chosen = mapping or (mappings[0] if mappings else None)
                if chosen not in mappings:
                    raise ValueError(f"OMX mapping not found: {chosen}")
                ids = list(file.mapping(chosen).keys())
                if zone not in ids:
                    raise ValueError(f"Zone ID not found in mapping {chosen}: {zone}")
                matrix = file[core]
                if matrix.shape != (len(ids), len(ids)):
                    raise ValueError(f"Core {core} does not match mapping {chosen}")
                if direction == 0:
                    logger.info(self.tr("Reading origin {} from core {}").format(zone, core))
                    values = matrix[ids.index(zone), :]
                elif direction == 1:
                    logger.info(self.tr("Reading destination {} from core {}").format(zone, core))
                    values = matrix[:, ids.index(zone)]
                else:
                    raise ValueError(f"Invalid slice direction: {direction}")
                fields = QgsFields()
                fields.append(QgsField("zone_id", QVariant.LongLong))
                fields.append(QgsField("data", QVariant.Double))
                sink, destination = self.parameterAsSink(
                    parameters, self.OUTPUT, context, fields, QgsWkbTypes.NoGeometry, QgsCoordinateReferenceSystem()
                )
                if sink is None:
                    raise QgsProcessingException(self.tr("Could not create zone values table"))
                logger.info(self.tr("Writing {} zone values to QGIS").format(len(ids)))
                progress_step = max(1, len(ids) // 100)
                for row, (zone_id, value) in enumerate(zip(ids, values), start=1):
                    if feedback.isCanceled():
                        del sink
                        return {}
                    feature = QgsFeature()
                    feature.setAttributes([int(zone_id), float(value)])
                    if not sink.addFeature(feature):
                        raise QgsProcessingException(self.tr("Could not write zone value"))
                    if row % progress_step == 0 or row == len(ids):
                        feedback.setProgress(99 * row / len(ids))
                del sink
                feedback.setProgress(100)
                logger.info(self.tr("Zone values table complete"))
                return {self.OUTPUT: destination}
        except (OSError, ValueError, KeyError) as error:
            raise QgsProcessingException(str(error)) from error

    def name(self):
        return "omxzoneslice"

    def displayName(self):
        return self.tr("OMX origin or destination to zone table")

    def group(self):
        return self.tr("Data")

    def groupId(self):
        return "data"

    def shortHelpString(self):
        return self.tr(
            "Reads one origin row or destination column from an OMX core into a zone_id/data table. Join zone_id to a zone layer for mapping."
        )

    def createInstance(self):
        return OmxZoneSlice()

    def tr(self, message):
        return trlt("OmxZoneSlice", message)


class TableToOmx(QgsProcessingAlgorithm):
    INPUT = "input"
    OUTPUT = "output"

    def initAlgorithm(self, configuration=None):
        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT, self.tr("OD table")))
        self.addParameter(QgsProcessingParameterFileDestination(self.OUTPUT, self.tr("OMX file"), "OpenMatrix (*.omx)"))

    @with_processing_feedback
    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.tr("Could not read OD table"))
        required = {"origin", "destination", "core", "value"}
        if not required.issubset(source.fields().names()):
            raise QgsProcessingException(self.tr("OD table requires origin, destination, core and value fields"))
        cells = {}
        ids = set()
        count = source.featureCount()
        feedback.setProgress(0)
        logger.info(self.tr("Reading and validating {} OD rows").format(count if count >= 0 else "unknown"))
        progress_step = max(1, count // 100) if count > 0 else 1000
        for row, feature in enumerate(source.getFeatures(), start=1):
            if feedback.isCanceled():
                return {}
            try:
                raw_origin, raw_destination = feature["origin"], feature["destination"]
                origin, destination = int(raw_origin), int(raw_destination)
                core = str(feature["core"])
                value = float(feature["value"])
                if origin != float(raw_origin) or destination != float(raw_destination):
                    raise ValueError("Zone IDs must be integers")
            except (TypeError, ValueError, OverflowError) as error:
                raise QgsProcessingException(self.tr("Invalid OD table row")) from error
            if not core or origin < 0 or destination < 0:
                raise QgsProcessingException(self.tr("Core must be nonempty and zone IDs must be nonnegative integers"))
            core_cells = cells.setdefault(core, {})
            key = (origin, destination)
            if key in core_cells:
                raise QgsProcessingException(self.tr("Duplicate OD cell: {}").format((core, *key)))
            core_cells[key] = value
            ids.update((origin, destination))
            if count > 0 and (row % progress_step == 0 or row == count):
                feedback.setProgress(50 * row / count)
        if not cells:
            raise QgsProcessingException(self.tr("OD table is empty"))
        zones = sorted(ids)
        size = len(zones) ** 2
        feedback.setProgress(50)
        logger.info(self.tr("Validating {} cores and {} zones").format(len(cells), len(zones)))
        for core, core_cells in cells.items():
            if feedback.isCanceled():
                return {}
            if len(core_cells) != size:
                raise QgsProcessingException(
                    self.tr("Every core must contain one value for every origin-destination pair")
                )
        output = self.parameterAsFileOutput(parameters, self.OUTPUT, context)
        path = Path(output)
        if path.exists():
            raise QgsProcessingException(self.tr("Output OMX file already exists: {}").format(output))
        positions = {zone: position for position, zone in enumerate(zones)}
        total = sum(len(core_cells) for core_cells in cells.values())
        completed = 0
        progress_step = max(1, total // 100)
        logger.info(self.tr("Writing OMX file: {}").format(output))
        try:
            with omx.open_file(output, "w") as file:
                file.create_mapping("zone_id", zones)
                for core, core_cells in sorted(cells.items()):
                    if feedback.isCanceled():
                        return {}
                    logger.info(self.tr("Writing core: {}").format(core))
                    matrix = np.empty((len(zones), len(zones)), dtype=np.float64)
                    for (origin, destination), value in core_cells.items():
                        if feedback.isCanceled():
                            return {}
                        matrix[positions[origin], positions[destination]] = value
                        completed += 1
                        if completed % progress_step == 0 or completed == total:
                            feedback.setProgress(50 + 49 * completed / total)
                    file[core] = matrix
        except Exception:
            path.unlink(missing_ok=True)
            raise
        finally:
            if feedback.isCanceled():
                path.unlink(missing_ok=True)
        feedback.setProgress(100)
        logger.info(self.tr("OMX file complete"))
        return {self.OUTPUT: output}

    def name(self):
        return "tabletoomx"

    def displayName(self):
        return self.tr("QGIS OD table to OMX")

    def group(self):
        return self.tr("Data")

    def groupId(self):
        return "data"

    def shortHelpString(self):
        return self.tr(
            "Writes a complete OD table (origin, destination, core, value) to a new OMX file. Each core must include every zone pair."
        )

    def createInstance(self):
        return TableToOmx()

    def tr(self, message):
        return trlt("TableToOmx", message)
