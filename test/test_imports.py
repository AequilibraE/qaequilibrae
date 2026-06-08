import logging
import os
import sys
from os.path import abspath, dirname, exists, join
from shutil import copyfile

import numpy as np
import pandas as pd
from qgis.PyQt.QtCore import QMetaType
from aequilibrae.matrix import AequilibraeMatrix
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
)
from qaequilibrae.modules.common_tools.data_layer_from_dataframe import layer_from_dataframe


def test_import_layer(folder_path):
    if not exists(folder_path):
        os.makedirs(folder_path)
    copyfile("test/data/NetworkPreparation/link.csv", f"{folder_path}/links.csv")

    csv_path = f"{folder_path}/links.csv"

    df = pd.read_csv(csv_path)

    layer = layer_from_dataframe(df, "links")

    if not layer.isValid():
        print("Layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(layer)
