"""Add a GTFS feed to an AequilibraE project."""

import json
import math
from qgis.core import (
    Qgis,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDateTime,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QDate

from aequilibrae.transit import Transit
from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.common_tools import project_has_transit
from qaequilibrae.modules.processing_provider.project import borrow_project
from qaequilibrae.modules.transit_procedures.gtfs_import_runner import import_gtfs_feeds


class AddGTFSFeedAlgorithm(QgsProcessingAlgorithm):
    """Import one GTFS feed into an existing AequilibraE project."""

    PROJECT = "PROJECT"
    GTFS_FEED = "GTFS_FEED"
    DATE = "DATE"
    AGENCY = "AGENCY"
    DESCRIPTION = "DESCRIPTION"
    CAPACITIES = "CAPACITIES"
    OPTIONS = "OPTIONS"
    ALLOW_MAP_MATCH = "ALLOW_MAP_MATCH"
    OPTIONS_VALUES = (
        "Overwrite Routes",
        "Add to Existing Routes",
        "Add transit table",
        "Create new route system",
    )

    def initAlgorithm(self, configuration: dict | None = None) -> None:
        self.addParameter(
            QgsProcessingParameterFile(
                self.PROJECT,
                self.tr("AequilibraE project folder"),
                behavior=Qgis.ProcessingFileParameterBehavior.Folder,
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                self.GTFS_FEED,
                self.tr("GTFS feed ZIP file"),
                behavior=Qgis.ProcessingFileParameterBehavior.File,
            )
        )
        self.addParameter(
            QgsProcessingParameterDateTime(
                self.DATE,
                self.tr("Service date"),
                type=Qgis.ProcessingDateTimeParameterDataType.Date,
            )
        )
        self.addParameter(QgsProcessingParameterString(self.AGENCY, self.tr("Agency")))
        self.addParameter(QgsProcessingParameterString(self.DESCRIPTION, self.tr("Description")))
        self.addParameter(
            QgsProcessingParameterString(
                self.CAPACITIES,
                self.tr("Vehicle capacities as a JSON object (optional)"),
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ALLOW_MAP_MATCH,
                self.tr("Allow map matching"),
                defaultValue=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.OPTIONS,
                self.tr("Transit import option"),
                options=list(self.OPTIONS_VALUES),
                usesStaticStrings=True,
            )
        )

    def processAlgorithm(
        self,
        parameters: dict,
        context: QgsProcessingContext,
        feedback: QgsProcessingFeedback | None,
    ) -> dict:
        project_path = self.parameterAsFile(parameters, self.PROJECT, context)
        feed_path = self.parameterAsFile(parameters, self.GTFS_FEED, context)
        selected_date = self.parameterAsDateTime(parameters, self.DATE, context)
        agency = self.parameterAsString(parameters, self.AGENCY, context).strip()
        description = self.parameterAsString(parameters, self.DESCRIPTION, context).strip()
        capacities_text = self.parameterAsString(parameters, self.CAPACITIES, context).strip()
        option_index = self.parameterAsEnum(parameters, self.OPTIONS, context)

        if not project_path or not feed_path or not selected_date.isValid():
            raise QgsProcessingException(self.tr("A project, GTFS feed, and valid service date are required."))
        if not agency or not description:
            raise QgsProcessingException(self.tr("Agency and description must not be empty."))
        if option_index < 0 or option_index >= len(self.OPTIONS_VALUES):
            raise QgsProcessingException(self.tr("Select a valid transit import option."))
        option = self.OPTIONS_VALUES[option_index]

        try:
            with borrow_project(project_path) as project:
                has_transit = project_has_transit(project)
                if has_transit and option not in self.OPTIONS_VALUES[:2]:
                    raise QgsProcessingException(
                        self.tr("Project already has transit tables. Choose overwrite or add to existing routes.")
                    )
                if not has_transit and option not in self.OPTIONS_VALUES[2:]:
                    raise QgsProcessingException(
                        self.tr("Project has no transit tables. Choose add transit table or create a route system.")
                    )

                transit = Transit(project)
                feed = transit.new_gtfs_builder(agency="", file_path=feed_path)
                date = selected_date.date()
                available_dates = [QDate.fromString(value, "yyyy-MM-dd") for value in feed.dates_available()]
                available_dates = [value for value in available_dates if value.isValid()]
                if available_dates and date not in available_dates:
                    raise QgsProcessingException(
                        self.tr(
                            f"Date {date.toString('yyyy-MM-dd')} is not available in this GTFS feed. "
                            f"Available dates: {', '.join(value.toString('yyyy-MM-dd') for value in available_dates)}"
                        )
                    )

                feed.set_date(date.toString("yyyy-MM-dd"))
                if capacities_text:
                    try:
                        capacities = json.loads(capacities_text)
                    except json.JSONDecodeError as error:
                        raise QgsProcessingException(self.tr("Capacities must be a valid JSON object.")) from error

                    def is_valid_capacity(value: object) -> bool:
                        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                            return False
                        try:
                            return math.isfinite(value)
                        except OverflowError:
                            return False

                    if not isinstance(capacities, dict) or any(
                        not isinstance(value, list)
                        or len(value) != 2
                        or any(not is_valid_capacity(item) for item in value)
                        for value in capacities.values()
                    ):
                        raise QgsProcessingException(
                            self.tr("Each capacity entry must contain a non-negative [seated, total] pair.")
                        )
                    feed.__capacities__ = capacities
                    transit.default_capacities = capacities
                feed.gtfs_data.agency.description = description
                feed.gtfs_data.agency.agency = agency
                if self.parameterAsBool(parameters, self.ALLOW_MAP_MATCH, context):
                    feed.set_allow_map_match()

                def report_import_progress(value: tuple) -> None:
                    if feedback is None:
                        return
                    if value[0] == "start":
                        feedback.setProgress(0)
                        feedback.pushInfo(str(value[2]))
                    elif value[0] == "update":
                        feedback.setProgress(float(value[1]))
                        feedback.pushInfo(str(value[2]))
                    elif value[0] == "set_text":
                        feedback.pushInfo(str(value[1]))

                import_gtfs_feeds(
                    project,
                    [feed],
                    overwrite=option == "Overwrite Routes",
                    signal_handler=report_import_progress,
                )
                if feedback is not None:
                    feedback.pushInfo(self.tr("GTFS feed import completed."))
                return {}
        except QgsProcessingException:
            raise
        except Exception as error:
            raise QgsProcessingException(self.tr(f"GTFS import failed: {error}")) from error

    def name(self) -> str:
        return "addGTFSFeed"

    def displayName(self) -> str:
        return self.tr("Add GTFS feed")

    def group(self) -> str:
        return self.tr("Transit")

    def groupId(self) -> str:
        return "transit"

    def createInstance(self) -> "AddGTFSFeedAlgorithm":
        return AddGTFSFeedAlgorithm()

    def tr(self, message: str) -> str:
        return trlt("ProcessingProvider", message)
