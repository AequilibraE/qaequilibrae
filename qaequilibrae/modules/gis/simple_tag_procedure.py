"""Run spatial tagging through Processing, then apply matches to the GUI layer."""

from aequilibrae.utils.interface.worker_thread import WorkerThread
from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsProcessingContext, QgsProcessingFeedback, QgsProcessingException, QgsProject

from qaequilibrae.modules.common_tools import get_vector_layer_by_name
from qaequilibrae.modules.processing_provider.mapping_procedures.simple_tag import SimpleTag, OPERATIONS


class SimpleTAG(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, flayer, tlayer, ffield, tfield, fmatch, tmatch, operation):
        super().__init__(parentThread)
        self.ffield = ffield
        self.tfield = tfield
        self.fmatch = fmatch
        self.tmatch = tmatch
        self.operation = operation
        self.error = None
        self.from_layer = get_vector_layer_by_name(flayer)
        self.to_layer = get_vector_layer_by_name(tlayer)
        self.all_attr = {}

    def doWork(self):
        feedback = QgsProcessingFeedback()
        self.signal.emit(["start", 100, self.tr("Performing spatial matching")])
        feedback.progressChanged.connect(
            lambda value: self.signal.emit(["update", value, "Performing spatial matching"])
        )
        try:
            field_index = self.to_layer.fields().lookupField(self.tfield)
            if field_index < 0:
                raise QgsProcessingException(self.tr(f"The target field '{self.tfield}' does not exist"))
            algorithm = SimpleTag()
            algorithm.initAlgorithm()
            context = QgsProcessingContext()
            context.setProject(QgsProject.instance())
            algorithm.processAlgorithm(
                {
                    algorithm.SOURCE: self.from_layer,
                    algorithm.SOURCE_FIELD: self.ffield,
                    algorithm.TARGET: self.to_layer,
                    algorithm.TARGET_FIELD: self.tfield,
                    algorithm.OPERATION: OPERATIONS.index(self.operation),
                    algorithm.MATCH_SOURCE_FIELD: self.fmatch or "",
                    algorithm.MATCH_TARGET_FIELD: self.tmatch or "",
                    algorithm.OUTPUT: "TEMPORARY_OUTPUT",
                },
                context,
                feedback,
            )
            self.all_attr = algorithm.matches
            # Keep the GUI's in-place semantics: unmatched features retain their values.
            if self.all_attr and not self.to_layer.dataProvider().changeAttributeValues(
                {feature_id: {field_index: value} for feature_id, value in self.all_attr.items()}
            ):
                raise QgsProcessingException(self.tr("Could not update the target layer"))
            self.to_layer.commitChanges()
            self.to_layer.updateFields()
        except Exception as error:
            self.error = str(error)
        finally:
            self.signal.emit(["finished"])
