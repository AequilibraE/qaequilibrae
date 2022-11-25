import os
import tempfile
import uuid

import numpy as np
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.utils.worker_thread import WorkerThread
from scipy.sparse import coo_matrix

from qgis.PyQt.QtCore import pyqtSignal


class LoadMatrix(WorkerThread):
    ProgressValue = pyqtSignal(object)
    ProgressText = pyqtSignal(object)
    ProgressMaxValue = pyqtSignal(object)
    finished_threaded_procedure = pyqtSignal(object)

    def __init__(self, parentThread, **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.matrix_type = kwargs.get("type")
        self.numpy_file = kwargs.get("file_path")
        self.layer = kwargs.get("layer")
        self.idx = kwargs.get("idx")
        self.sparse = kwargs.get("sparse", False)

        self.matrix = None
        self.matrix_hash = None
        self.titles = None
        self.report = []

    def doWork(self):
        if self.matrix_type == "layer":
            self.ProgressText.emit("Loading from table")
            feat_count = self.layer.featureCount()
            self.ProgressMaxValue.emit(feat_count)

            # We read all the vectors and put in a list of lists
            matrix = []
            P = 0
            for feat in self.layer.getFeatures():
                P += 1
                a = feat.attributes()[self.idx[0]]
                b = feat.attributes()[self.idx[1]]
                c = feat.attributes()[self.idx[2]]
                matrix.append([a, b, c])
                if P % 1000 == 0:
                    self.ProgressValue.emit(int(P))
                    self.ProgressText.emit(("Loading matrix: " + "{:,}".format(P) + "/" + "{:,}".format(feat_count)))

            self.ProgressValue.emit(0)
            self.ProgressText.emit("Converting to a NumPy array")

            matrix1 = np.array(matrix)  # transform the list of lists in NumPy array
            del matrix

            # Bring it all to memory mapped
            self.matrix = np.memmap(
                os.path.join(tempfile.gettempdir(), "aequilibrae_temp_file_" + str(uuid.uuid4().hex) + ".mat"),
                dtype=[("from", np.uint64), ("to", np.uint64), ("flow", np.float64)],
                mode="w+",
                shape=(int(matrix1.shape[0]),),
            )

            self.matrix["from"] = matrix1[:, 0]
            self.matrix["to"] = matrix1[:, 1]
            self.matrix["flow"] = matrix1[:, 2]
            del matrix1

        elif self.matrix_type == "numpy":
            self.ProgressText.emit("Loading from NumPy")
            try:
                mat = np.load(self.numpy_file)
                if len(mat.shape[:]) == 2:
                    mat = coo_matrix(mat)
                    cells = int(mat.row.shape[0])
                    self.matrix = np.memmap(
                        os.path.join(tempfile.gettempdir(), AequilibraeMatrix().random_name() + ".mat"),
                        dtype=[("from", np.uint64), ("to", np.uint64), ("flow", np.float64)],
                        mode="w+",
                        shape=(cells,),
                    )
                    self.matrix["from"][:] = mat.row[:]
                    self.matrix["to"] = mat.col[:]
                    self.matrix["flow"][:] = mat.data[:]
                    del mat
                else:
                    self.report.append(
                        "Numpy array needs to be 2 dimensional. Matrix provided has " + str(len(mat.shape[:]))
                    )
            except Exception as e:
                self.report.append(f"Could not load array. {e.args}")

        self.ProgressText.emit("")
        self.finished_threaded_procedure.emit("LOADED-MATRIX")
