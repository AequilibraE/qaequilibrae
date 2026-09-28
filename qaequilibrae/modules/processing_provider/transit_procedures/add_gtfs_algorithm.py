""" Add a GTFS feed to the QAequilibrae model. """

from copy import deepcopy

from qgis.core import (
    Qgis,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProcessingParameterDateTime,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFile,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QDate

from qaequilibrae.i18n.translate import trlt
from aequilibrae.project import Project
from aequilibrae.transit import Transit
from qaequilibrae.modules.common_tools import (
    project_has_transit,
    quote_identifier,
)

class AddGTFSFeedAlgorithm(QgsProcessingAlgorithm):
    """ """

    def initAlgorithm(self, config: dict | None = None) -> None:
        self.addParameter(
            QgsProcessingParameterFile(
                name="PROJECT",
                description=self.tr("Qgis Project"),
                behavior=QgsProcessingParameterFile.Folder
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                name="QTFS_FEED",
                description=self.tr("QTFS Feed"),
                behavior=QgsProcessingParameterFile.File
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

        self.addParameter(
            QgsProcessingParameterEnum(
                name="OPTIONS",
                description=self.tr("Resetting Transit Tables"),
                options=["Overwrite Routes", "Add to Existing Routes", "Add transit table", "Create new route system"],
                usesStaticStrings=True
            )
        )

    def processAlgorithm(self, parameters: dict, context: QgsProcessingContext, feedbkac: QgsProcessingFeedback):
        project_path = self.parameterAsFile(parameters, "PROJECT", context)

        qtfs_feed = self.parameterAsFile(parameters, "QTFS_FEED", context)

        date = self.parameterAsDateTime(parameters, "DATE", context).date()

        agency: str = self.parameterAsString(parameters, "AGENCY", context)

        description: str = self.parameterAsString(parameters, "DESCRIPTION", context)

        option: list[str] = self.parameterAsString(parameters, "OPTIONS", context)

        # TODO: do various checks
        # include checks for option based on whether gtfs already exists

        self.qgis_project = Project()
        
        try:
            self.qgis_project.open(project_path)
        except FileNotFoundError as e:
            if e.args[0] == "Model does not exist. Check your path and try again":
                raise QgsProcessingException("Folder does not contain an Aequilibrae model. Check your path and try again.")
            else:
                raise e

        # add the feed
        self._p = Transit(self.qgis_project)
        self.set_data(qtfs_feed, date)

        # raise ValueError(f"Date: {date}, should work: {date in self.feed.gtfs_data.feed_dates}, type of date: {type(date)}, type of dates: {type(self.feed.gtfs_data.feed_dates[0])}")
        # self.feed.set_date(date.toString("yyyy-MM-dd"))

        self.feed.gtfs_data.agency.description = description
        self.feed.gtfs_data.agency.agency = agency


        if option == "Overwrite Routes":
            __transit_tables = [
                        "agencies",
                        "fare_attributes",
                        "fare_rules",
                        "fare_zones",
                        "pattern_mapping",
                        "route_links",
                        "routes",
                        "stop_connectors",
                        "stops",
                        "trips",
                        "trips_schedule",
                    ]
            with self.qgis_project.transit_connection as conn:
                for table in __transit_tables:
                    conn.execute(f"DELETE FROM {quote_identifier(table)};")

        self.feed.signal.connect(self.signal_handler)
        self.feed.execute_import()

        # self.qgis_project.projectManager.removeTab(0)
        # self.qgis_project.update_project_layers()

        self.qgis_project.close()

        return {}
    
    def set_data(self, source_path_file, date):
        self.feed = self._p.new_gtfs_builder(agency="", file_path=source_path_file)
        if dates := self.feed.dates_available():
            # check the provided date is within the right range
            dates = [QDate.fromString(dt, "yyyy-MM-dd") for dt in dates]
            min_date = min(dates)
            max_date = max(dates)
            if (date > max_date or date < min_date):
                raise QgsProcessingException(f"Date needs to be between {min_date} and {max_date} for this data. Date was: {date}")
            if (date not in dates):
                raise QgsProcessingException(f"Date {date} is not available in this GTFS feed. Potential dates are: {dates}")
        self.default_capacities = deepcopy(self._p.default_capacities)

    def signal_handler(self, val):
        if val[0] == "start":
            self.progress_bridge.progress_started.emit(val[1], val[2])
        elif val[0] == "update":
            self.progress_bridge.stage_line.emit(val[2])
            self.progress_bridge.progress_updated.emit(val[1])
        elif val[0] == "set_text":
            self.progress_bridge.progress_reset.emit()
            self.progress_bridge.stage_line.emit(val[1])
        elif val[0] == "finished":
            self.progress_bridge.finished.emit()

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

