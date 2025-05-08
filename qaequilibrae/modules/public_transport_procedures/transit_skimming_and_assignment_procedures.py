from qgis.PyQt.QtCore import pyqtSignal
from aequilibrae.utils.interface.worker_thread import WorkerThread
from aequilibrae.paths import TransitAssignment, TransitClass


class TransitSkimAssignProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, graph, matrix, parameters):
        WorkerThread.__init__(self, parentThread)
        self.parameters = parameters
        self.matrix = matrix
        self.graph = graph

    def doWork(self):
        # Create the Transit Class
        assigclass = TransitClass(name=self.parameters["class_name"], graph=self.graph, matrix=self.matrix)

        # Create the Transit Assignment Class
        self.assig = TransitAssignment()
        self.assig.add_class(assigclass)

        # Set assignment
        self.assig.set_time_field(self.parameters["time_field"])
        self.assig.set_frequency_field(self.parameters["frequency_field"])
        self.assig.set_skimming_fields(self.parameters["skimming_fields"])
        self.assig.set_algorithm("os")
        assigclass.set_demand_matrix_core(self.parameters["demand_matrix_core"])

        # Perform the assignment
        self.assig.execute()

        self.signal.emit(["finished"])
