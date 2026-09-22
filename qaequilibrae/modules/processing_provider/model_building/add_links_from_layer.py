import importlib.util as iutil
import sys
from string import ascii_letters

from qgis.core import Qgis, QgsProcessingMultiStepFeedback, QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingException, QgsProcessingParameterField, QgsProcessingParameterFile

from qaequilibrae.i18n.translate import trlt
from qaequilibrae.modules.common_tools import geodataframe_from_layer

from ..geometry_io.project import open_project


class AddLinksFromLayer(QgsProcessingAlgorithm):
    def initAlgorithm(self, configuration=None):
        self.addParameter(
            QgsProcessingParameterFile(
                "project_path",
                self.tr("Project path"),
                behavior=Qgis.ProcessingFileParameterBehavior.Folder,
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "links",
                self.tr("Links"),
                types=[Qgis.ProcessingSourceType.VectorLine],
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "direction",
                self.tr("Direction"),
                type=Qgis.ProcessingFieldParameterDataType.Numeric,
                parentLayerParameterName="links",
                allowMultiple=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "link_type",
                self.tr("Link type"),
                type=Qgis.ProcessingFieldParameterDataType.String,
                parentLayerParameterName="links",
                allowMultiple=False,
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "modes",
                self.tr("Modes"),
                type=Qgis.ProcessingFieldParameterDataType.String,
                parentLayerParameterName="links",
                allowMultiple=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        feedback = QgsProcessingMultiStepFeedback(5, feedback)
        feedback.pushInfo(self.tr("Opening project"))

        project_path = parameters.get("project_path")
        if project_path is None:
            project_path = self.parameterAsFile(parameters, "project_path", context)
        with open_project(project_path) as project:
            feedback.pushInfo(self.tr("Importing links layer"))

            layer = self.parameterAsVectorLayer(parameters, "links", context)
            if layer is None:
                raise QgsProcessingException(self.tr("Links layer could not be loaded"))
            gdf = geodataframe_from_layer(layer).infer_objects()

            columns = [parameters["link_type"], parameters["direction"], parameters["modes"], "geometry"]
            gdf = gdf[columns]
            gdf.columns = ["link_type", "direction", "modes", "geometry"]

            all_modes = set("".join(gdf["modes"].unique()))
            modes = project.network.modes
            current_modes = list(modes.all_modes().keys())
            for mode_id in [mode for mode in all_modes if mode not in current_modes]:
                new_mode = modes.new(mode_id)
                new_mode.mode_name = mode_id
                new_mode.description = "Mode automatically added during project creation from layers"
                modes.add(new_mode)
                new_mode.save()

            all_link_types = gdf["link_type"].unique()
            link_types = project.network.link_types
            current_link_types = [link_type.link_type for link_type in link_types.all_types().values()]
            letters = [letter for letter in ascii_letters if letter not in link_types.all_types()]
            for link_type_name in [name for name in all_link_types if name not in current_link_types]:
                if not letters:
                    raise QgsProcessingException(self.tr("No unused link type identifiers are available"))
                new_link_type = link_types.new(letters.pop(0))
                new_link_type.link_type = link_type_name
                new_link_type.description = "Link type automatically added during project creation from layers"
                new_link_type.save()

            feedback.pushInfo(self.tr("Adding links"))
            links = project.network.links
            for _, record in gdf.iterrows():
                if feedback.isCanceled():
                    break
                new_link = links.new()
                new_link.direction = record.direction
                new_link.modes = record.modes
                new_link.link_type = record.link_type
                new_link.geometry = record.geometry
                new_link.save()

            links.refresh()
            link_count = project.network.count_links()

        feedback.pushInfo(self.tr("Closing project"))
        return {"Output": link_count}

    def name(self):
        return "addlinksfromlayer"

    def displayName(self):
        return self.tr("Add links from layer to project")

    def group(self):
        return self.tr("Model building")

    def groupId(self):
        return "model_building"

    def shortHelpString(self):
        return self.tr("Adds links from a layer to an existing AequilibraE project")

    def createInstance(self):
        return AddLinksFromLayer()

    def tr(self, message):
        return trlt("AddLinksFromLayer", message)
