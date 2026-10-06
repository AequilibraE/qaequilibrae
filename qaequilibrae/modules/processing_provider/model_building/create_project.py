"""Create projects from link layers or OpenStreetMap without opening dialogs."""

import re
from contextlib import contextmanager
from pathlib import Path
from string import ascii_letters

from qgis.core import (
    Qgis,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterField,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterString,
)

from qaequilibrae.modules.network.node_numbering import reserve_node_ids_for_centroids

from ..geometry_io.common import copy_record_attributes, ignored_input_fields, source_rows
from ..project_algorithm import ProcessingAlgorithm


@contextmanager
def new_project(folder):
    from aequilibrae import Project
    from aequilibrae.context import activate_project, get_active_project

    if Path(folder).exists():
        raise QgsProcessingException("The output project folder must not exist")
    active = get_active_project(must_exist=False)
    project = Project()
    try:
        project.new(folder)
        reserve_node_ids_for_centroids(project)
        yield project
    finally:
        project.close()
        activate_project(active)


class CreateProjectFromLinkLayer(ProcessingAlgorithm):
    algorithm_name = "projectfromlayer"
    display_name = "Create project from link layer"
    group_name = "Model building"
    group_id = "model_building"

    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource("INPUT", self.tr("Links"), [Qgis.ProcessingSourceType.VectorLine])
        )
        for name, label, kind, optional in (
            ("DIRECTION", "Direction field", Qgis.ProcessingFieldParameterDataType.Numeric, False),
            ("MODES", "Modes field", Qgis.ProcessingFieldParameterDataType.String, False),
            ("LINK_TYPE", "Link type field", Qgis.ProcessingFieldParameterDataType.String, False),
            ("SOURCE_ID", "Source link ID field", Qgis.ProcessingFieldParameterDataType.Any, True),
        ):
            self.addParameter(
                QgsProcessingParameterField(
                    name,
                    self.tr(label),
                    parentLayerParameterName="INPUT",
                    type=kind,
                    optional=optional,
                )
            )
        self.addParameter(
            QgsProcessingParameterBoolean("COPY_FIELDS", self.tr("Import additional link fields"), defaultValue=True)
        )
        self.addParameter(QgsProcessingParameterFolderDestination("OUTPUT", self.tr("New project folder")))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, "INPUT", context)
        if source is None:
            raise QgsProcessingException(self.tr("The links layer could not be loaded"))
        fields = {
            key: self.parameterAsString(parameters, key, context).lower()
            for key in ("DIRECTION", "MODES", "LINK_TYPE", "SOURCE_ID")
        }
        rows = source_rows(source)
        mode_ids = set()
        type_names = set()
        for row in rows:
            direction = row.get(fields["DIRECTION"])
            modes = row.get(fields["MODES"])
            link_type = row.get(fields["LINK_TYPE"])
            if direction not in (-1, 0, 1) or not isinstance(modes, str) or not modes:
                raise QgsProcessingException(self.tr("Links require direction -1, 0 or 1 and nonempty mode IDs"))
            if not isinstance(link_type, str) or not re.fullmatch(r"[A-Za-z_]+", link_type):
                raise QgsProcessingException(self.tr("Link type names must contain only letters and underscores"))
            if row["geometry"] is None or row["geometry"].geom_type != "LineString" or row["geometry"].is_empty:
                raise QgsProcessingException(self.tr("Each link must have a LineString geometry"))
            mode_ids.update(modes)
            type_names.add(link_type)
        if not mode_ids.issubset(ascii_letters):
            raise QgsProcessingException(self.tr("Mode IDs must be single letters"))
        copy_fields = self.parameterAsBool(parameters, "COPY_FIELDS", context)
        ignored = ignored_input_fields("links", adding=True) | {"link_id", "source_id"} | set(fields.values())
        extra_fields = (
            [field for field in source.fields() if field.name().lower() not in ignored] if copy_fields else []
        )
        for field in extra_fields:
            if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", field.name()):
                raise QgsProcessingException(self.tr(f"Invalid project field name: {field.name()}"))
        if feedback.isCanceled():
            return {}
        output = self.parameterAsString(parameters, "OUTPUT", context)
        with new_project(output) as project:
            for identifier in sorted(mode_ids - set(project.network.modes.all_modes())):
                mode = project.network.modes.new(identifier)
                mode.mode_name = identifier
                project.network.modes.add(mode)
            types = project.network.link_types
            missing_types = type_names - {value.link_type for value in types.all_types().values()}
            free_ids = [letter for letter in ascii_letters if letter not in types.all_types()]
            if len(missing_types) > len(free_ids):
                raise QgsProcessingException(self.tr("No unused link type identifiers are available"))
            for name, identifier in zip(sorted(missing_types), free_ids):
                link_type = types.new(identifier)
                link_type.link_type = name
                link_type.save()
            links = project.network.links
            existing_fields = set(links.data.columns)
            for field in extra_fields:
                name = field.name().lower()
                if name not in existing_fields:
                    kind = "INTEGER" if "int" in field.typeName().lower() else "REAL"
                    links.fields.add(name, "Imported from link layer", kind if field.isNumeric() else "TEXT")
                    existing_fields.add(name)
            if fields["SOURCE_ID"]:
                field = source.fields().at(source.fields().lookupField(fields["SOURCE_ID"]))
                kind = "INTEGER" if "int" in field.typeName().lower() else "REAL"
                links.fields.add(
                    "source_id", "Link identifier from the source layer", kind if field.isNumeric() else "TEXT"
                )
            links.refresh_fields()
            for index, row in enumerate(rows):
                if feedback.isCanceled():
                    break
                link = links.new()
                if copy_fields:
                    copy_record_attributes(link, links, row, ignored, skip_nulls=True)
                link.direction = int(row[fields["DIRECTION"]])
                link.modes = row[fields["MODES"]]
                link.link_type = row[fields["LINK_TYPE"]]
                if fields["SOURCE_ID"]:
                    link.source_id = row[fields["SOURCE_ID"]]
                link.geometry = row["geometry"]
                link.save()
                feedback.setProgress(100 * (index + 1) / len(rows))
            links.fields.save()
        return {"OUTPUT": output}

    def shortHelpString(self):
        return self.tr(
            "Creates a project from links. Nodes are generated from link endpoints. "
            "Source IDs are stored in source_id. Additional fields use lowercase input names. "
            "The output folder must not exist. Cancellation can leave a partial project."
        )


class CreateProjectFromOSM(ProcessingAlgorithm):
    algorithm_name = "projectfromosm"
    display_name = "Create project from OSM"
    group_name = "Model building"
    group_id = "model_building"

    def initAlgorithm(self, configuration=None):
        self.addParameter(QgsProcessingParameterString("PLACE", self.tr("Place name"), optional=True))
        self.addParameter(QgsProcessingParameterExtent("EXTENT", self.tr("Download extent"), optional=True))
        self.addParameter(
            QgsProcessingParameterString(
                "MODES", self.tr("OSM mode names (comma-separated)"), defaultValue="car,transit,bicycle,walk"
            )
        )
        self.addParameter(QgsProcessingParameterFolderDestination("OUTPUT", self.tr("New project folder")))

    def processAlgorithm(self, parameters, context, feedback):
        from qgis.core import QgsCoordinateReferenceSystem
        from shapely.geometry import box

        place = self.parameterAsString(parameters, "PLACE", context).strip()
        has_extent = bool(parameters.get("EXTENT"))
        if bool(place) == has_extent:
            raise QgsProcessingException(self.tr("Supply either a place name or a download extent"))
        modes = [
            mode.strip() for mode in self.parameterAsString(parameters, "MODES", context).split(",") if mode.strip()
        ]
        if not modes:
            raise QgsProcessingException(self.tr("At least one OSM mode name is required"))
        area = None
        if has_extent:
            extent = self.parameterAsExtent(parameters, "EXTENT", context, QgsCoordinateReferenceSystem("EPSG:4326"))
            if extent.isEmpty():
                raise QgsProcessingException(self.tr("The download extent is empty"))
            area = box(extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum())
        if feedback.isCanceled():
            return {}
        output = self.parameterAsString(parameters, "OUTPUT", context)
        with new_project(output) as project:
            feedback.pushInfo(self.tr("Downloading and building the OSM network"))
            project.network.create_from_osm(model_area=area, place_name=place or None, modes=modes)
            # The OSM importer restores the library's triggers during its build.
            reserve_node_ids_for_centroids(project)
        return {"OUTPUT": output}

    def shortHelpString(self):
        return self.tr(
            "Downloads an OSM network by place name or extent. Internet access is required. "
            "Mode names are OSM names, such as car or walk. The output folder must not exist. "
            "Cancellation cannot interrupt the OSM download and build; failures can leave a partial project."
        )
