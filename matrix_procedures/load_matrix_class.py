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


class MatrixReblocking(WorkerThread):
    def __init__(self, parentThread, **kwargs):
        WorkerThread.__init__(self, parentThread)
        self.matrix = AequilibraeMatrix()
        self.matrices = kwargs.get("matrices")
        self.sparse = kwargs.get("sparse", False)
        self.file_name = kwargs.get("file_name", AequilibraeMatrix().random_name())

        self.num_matrices = len(self.matrices.keys())
        self.matrix_hash = {}
        self.titles = []
        self.report = []

    def doWork(self):
        if self.sparse:
            # Builds the hash
            self.ProgressMaxValue.emit(self.num_matrices)
            self.ProgressValue.emit(0)
            self.ProgressText.emit("Building correspondence")

            indices = None
            p = 0
            for mat_name, mat in self.matrices.items():
                # Gets all non-zero coordinates and makes sure that they are considered
                froms = mat["from"]
                tos = mat["to"]

                if indices is None:
                    all_indices = np.hstack((froms, tos))
                else:
                    all_indices = np.hstack((indices, froms, tos))
                indices = np.unique(all_indices)
                p += 1
                self.ProgressValue.emit(p)
            compact_shape = int(indices.shape[0])
        else:
            compact_shape = 0
            for mat_name, mat in self.matrices.items():
                compact_shape = np.max(compact_shape, mat.shape[0])
            indices = np.arange(compact_shape)

        new_index = {k: i for i, k in enumerate(indices)}

        names = [str(n) for n in self.matrices.keys()]
        self.matrix.create_empty(
            file_name=self.file_name, zones=compact_shape, matrix_names=names, data_type=np.float64
        )

        self.matrix.index[:] = indices[:]

        k = 0
        self.ProgressMaxValue.emit(self.num_matrices)
        self.ProgressText.emit("Reblocking matrices")

        new_mat = None
        for mat_name, mat in self.matrices.items():
            if self.sparse:
                new_mat = np.copy(mat)
                for j, v in new_index.items():
                    new_mat["from"][mat["from"] == j] = v
                    new_mat["to"][mat["to"] == j] = v
                k += 1
                self.ProgressValue.emit(k)
            else:
                k += 1
                self.ProgressValue.emit(1)

            # In order to differentiate the zeros from the NaNs in the future matrix
            if new_mat is None:
                raise ValueError("Could not create reblocked matrix.")
            new_mat["flow"][new_mat["flow"] == 0] = np.inf

            # Uses SciPy Sparse matrices to build the compact one
            mat = coo_matrix((new_mat["flow"], (new_mat["from"], new_mat["to"])), shape=(compact_shape, compact_shape))
            self.matrix.matrix[mat_name][:, :] = mat.toarray().astype(np.float64)

            # In order to differentiate the zeros from the NaNs in the future matrix
            self.matrix.matrix[mat_name][self.matrix.matrix[mat_name] == 0] = np.nan
            self.matrix.matrix[mat_name][self.matrix.matrix[mat_name] == np.inf] = 0

            del mat
            del new_mat

        self.ProgressText.emit("Matrix Reblocking finalized")
        self.finished_threaded_procedure.emit("REBLOCKED MATRICES")
