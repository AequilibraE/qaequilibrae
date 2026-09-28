""" Add a GTFS feed to the QAequilibrae model. """

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, cast

import numpy as np
import pandas as pd
from shapely.geometry import LineString

from qgis.core import (
    Qgis,
    QgsFeature,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)

from qaequilibrae.i18n.translate import trlt

class AddGTFSFeedAlgorithm(QgsProcessingAlgorithm):
    """ """

    def name(self) -> str:
        return "addGTFSFeed"

    def displayName(self) -> str:
        return "Add GTFS feed"
    
    def group(self) -> str:
        return "Transit"

    def groupId(self) -> str:
        return "transit"

    def createInstance(self) -> "AddGTFSFeedAlgorithm":
        return AddGTFSFeedAlgorithm()
