"""Adapt the desire-line GUI to the registered mapping Processing algorithms."""

from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.utils.interface.worker_thread import WorkerThread
from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsProcessingContext, QgsProcessingFeedback, QgsVectorLayer

from qaequilibrae.modules.common_tools import get_vector_layer_by_name
from qaequilibrae.modules.processing_provider.mapping_procedures.delaunay_network import DelaunayNetwork
from qaequilibrae.modules.processing_provider.mapping_procedures.desire_lines import DesireLines
from qaequilibrae.qgis_logging import get_logger


class _MappingFeedback(QgsProcessingFeedback):
    def __init__(self, report):
        super().__init__()
        self.report = report

    def pushWarning(self, message):
        super().pushWarning(message)
        self.report.append(message)


class DesireLinesProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, layer: str, id_field: str, matrix: AequilibraeMatrix, dl_type: str) -> None:
        super().__init__(parentThread)
        self.layer = layer
        self.id_field = id_field
        self.matrix = matrix
        self.dl_type = dl_type
        self.error = None
        self.report = []
        self.result_layer: QgsVectorLayer | None = None
        self.logger = get_logger(__name__)

    def doWork(self):
        feedback = _MappingFeedback(self.report)
        self.signal.emit(["start", 100, self.tr("Creating mapping layer")])
        feedback.progressChanged.connect(lambda value: self.signal.emit(["update", value, ""]))
        try:
            is_delaunay = self.dl_type == "DelaunayLines"
            algorithm = DelaunayNetwork() if is_delaunay else DesireLines()
            algorithm.initAlgorithm()
            algorithm.matrix = self.matrix  # Borrow the GUI's selected cores, including in-memory matrices.
            context = QgsProcessingContext()
            parameters = {
                "NODES" if is_delaunay else "ZONES": get_vector_layer_by_name(self.layer),
                "NODE_ID_FIELD" if is_delaunay else "ZONE_ID_FIELD": self.id_field,
                "BLOCK_CENTROID_FLOWS": False,  # Keep the GUI's legacy Delaunay assignment policy.
                "OUTPUT": "TEMPORARY_OUTPUT",
            }
            outputs = algorithm.processAlgorithm(parameters, context, feedback)
            result = context.takeResultLayer(outputs["OUTPUT"])
            assert isinstance(result, QgsVectorLayer)
            result.setName(self.dl_type)
            # Retain the field names used by existing GUI-created layers.
            result.dataProvider().renameAttributes(
                {
                    result.fields().lookupField(name): legacy
                    for name, legacy in (("a_node", "A_Node"), ("b_node", "B_Node"), ("direction", "direct"))
                }
            )
            result.updateFields()
            self.result_layer = result
            count = result.featureCount()
            label = self.tr("Building resulting layer") if is_delaunay else self.tr("Creating Desire Lines")
            self.signal.emit(["start", count, label])
            self.signal.emit(["update", count, ""])
        except Exception as error:
            self.error = str(error)
            self.report.append(self.error)
            self.logger.exception("Could not create mapping layer")
        finally:
            self.signal.emit(["finished"])
