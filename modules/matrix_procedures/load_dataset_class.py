from qgis.PyQt.QtCore import QVariant
import numpy as np
from aequilibrae.utils.worker_thread import WorkerThread
import struct
from aequilibrae.matrix import AequilibraeData
from ..common_tools.global_parameters import float_types, string_types, integer_types
from qgis.PyQt.QtCore import pyqtSignal


class LoadDataset(WorkerThread):
    ProgressText = pyqtSignal(object)
    ProgressValue = pyqtSignal(object)
    ProgressMaxValue = pyqtSignal(object)
    finished_threaded_procedure = pyqtSignal(object)

    def __init__(self, parent_thread, layer, index_field, fields, file_name):
        WorkerThread.__init__(self, parent_thread)
        self.layer = layer
        self.index_field = index_field
        self.fields = fields
        self.error = None
        self.python_version = 8 * struct.calcsize("P")
        self.output = AequilibraeData()
        self.output_name = file_name

    def doWork(self):
        feat_count = self.layer.featureCount()
        self.ProgressMaxValue.emit(feat_count)

        # Create specification for the output file
        datafile_spec = {"entries": feat_count}
        if self.output_name is None:
            datafile_spec["memory_mode"] = True
        else:
            datafile_spec["memory_mode"] = False
        fields = []
        types = []
        idxs = []
        empties = []
        for field in self.layer.dataProvider().fields().toList():
            if field.name() in self.fields:
                if field.type() in integer_types:
                    types.append("<i8")
                    empties.append(np.iinfo(np.int64).min)
                elif field.type() in float_types:
                    types.append("<f8")
                    empties.append(np.nan)
                elif field.type() in string_types:
                    types.append("S" + str(field.length()))
                    empties.append("")
                else:
                    self.error = "Field {} does has a type not supported.".format(str(field.name()))
                    break
                fields.append(str(field.name()))
                idxs.append(self.layer.dataProvider().fieldNameIndex(field.name()))

        index_idx = self.layer.dataProvider().fieldNameIndex(self.index_field)
        datafile_spec["field_names"] = fields
        datafile_spec["data_types"] = types
        datafile_spec["file_path"] = self.output_name

        if self.error is None:
            self.output.create_empty(**datafile_spec)

            # Get all the data
            for p, feat in enumerate(self.layer.getFeatures()):
                for idx, field, empty in zip(idxs, fields, empties):
                    if feat.attributes()[idx] == QVariant():
                        self.output.data[field][p] = empty
                    else:
                        self.output.data[field][p] = feat.attributes()[idx]
                self.output.index[p] = feat.attributes()[index_idx]
                self.ProgressValue.emit(p)

            self.ProgressValue.emit(feat_count)
        self.finished_threaded_procedure.emit("Done")
