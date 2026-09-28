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
    QgsProcessingParameterDateTime,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)

from qaequilibrae.i18n.translate import trlt

class AddGTFSFeedAlgorithm(QgsProcessingAlgorithm):
    """ """

    def initAlgorithm(self, config: dict | None = None) -> None:
        self.addParameter(
            QgsProcessingParameterFile(
                name="QGIS_PROJECT",
                description=self.tr("Qgis Project"),
                behavior=QgsProcessingParameterFile.Folder
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                name="QTFS_FEED",
                description=self.tr("QTFS Feed"),
                behavior=QgsProcessingParameterFile.Folder
            )
        )

        self.addParameter(
            QgsProcessingParameterDateTime(
                name="DATE",
                description=self.tr("Date"),
                type=Qgis.ProcessingDateTimeParameterDataType.Date
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name="AGENCY",
                description=self.tr("Agency")
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                name="DESCRIPTION",
                description=self.tr("Description")
            )
        )

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
    
    def tr(self, message: str) -> str:
        return trlt("DesireLines", message)

