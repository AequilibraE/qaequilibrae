from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import numpy as np
from aequilibrae.utils.interface.worker_thread import WorkerThread
from qgis.PyQt.QtCore import pyqtSignal


class LoadMatrix(WorkerThread):
    signal = pyqtSignal(object)

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
        feat_count = self.layer.featureCount()
        self.signal.emit(["start", feat_count, self.tr("Loading from table")])

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
                txt = self.tr("Loading matrix: {}/{}").format(P, feat_count)
                self.signal.emit(["update", int(P), txt])

        self.signal.emit(["set_text", self.tr("Converting to a NumPy array")])

        matrix1 = np.array(matrix)  # transform the list of lists in NumPy array
        del matrix

        # Bring it all to memory mapped
        self.matrix = np.memmap(
            Path(gettempdir()) / f"aequilibrae_temp_file_{uuid4().hex}.mat",
            dtype=[("from", np.uint64), ("to", np.uint64), ("flow", np.float64)],
            mode="w+",
            shape=(int(matrix1.shape[0]),),
        )

        self.matrix["from"] = matrix1[:, 0]
        self.matrix["to"] = matrix1[:, 1]
        self.matrix["flow"] = matrix1[:, 2]
        del matrix1

        self.signal.emit(["finished", "LOADED-MATRIX"])
