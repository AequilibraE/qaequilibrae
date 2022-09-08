import numpy as np
from aequilibrae.matrix import AequilibraeMatrix
from aequilibrae.utils.worker_thread import WorkerThread
from scipy.sparse import coo_matrix

from qgis.PyQt.QtCore import pyqtSignal


class MatrixReblocking(WorkerThread):
    ProgressValue = pyqtSignal(object)
    ProgressText = pyqtSignal(object)
    ProgressMaxValue = pyqtSignal(object)
    finished_threaded_procedure = pyqtSignal(object)

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
