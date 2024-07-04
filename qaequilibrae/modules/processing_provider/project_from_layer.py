import importlib.util as iutil
import pandas as pd
import sys
from os.path import join
from string import ascii_lowercase
from shapely.wkt import loads as load_wkt

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProcessingAlgorithm
from qgis.core import QgsProcessing, QgsProcessingMultiStepFeedback, QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterField, QgsProcessingParameterFile, QgsProcessingParameterString
from qgis.core import QgsProject, QgsFeature, QgsVectorLayer, QgsDataSourceUri

from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.i18n.translate import trlt


class ProjectFromLayer(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "links", self.tr("Links"), types=[QgsProcessing.TypeVectorLine], defaultValue=None
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "link_id",
                self.tr("Link ID"),
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName="links",
                allowMultiple=False,
                defaultValue="link_id",
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "link_type",
                self.tr("Link type"),
                type=QgsProcessingParameterField.String,
                parentLayerParameterName="links",
                allowMultiple=False,
                defaultValue="link_type",
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "direction",
                self.tr("Direction"),
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName="links",
                allowMultiple=False,
                defaultValue="direction",
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                "modes",
                self.tr("Modes"),
                type=QgsProcessingParameterField.String,
                parentLayerParameterName="links",
                allowMultiple=False,
                defaultValue="modes",
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                "dst",
                self.tr("Output folder"),
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=standard_path(),
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                "project_name", self.tr("Project name"), multiLine=False, defaultValue="new_project"
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)

        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae import Project

        feedback.pushInfo(self.tr("Creating project"))
        project_path = join(parameters["dst"], parameters["project_name"])
        project = Project()
        project.new(project_path)

        feedback.pushInfo(self.tr("Importing links layer"))
        aeq_crs = QgsCoordinateReferenceSystem("EPSG:4326")

        # Adding source_id field early to have all fields available in links table
        links = project.network.links
        link_data = links.fields
        link_data.add("source_id", "link_id from the data source")
        links.refresh_fields()
        uri = QgsDataSourceUri()
        uri.setDatabase(join(project_path,'project_database.sqlite'))
        uri.setDataSource('', 'links', 'geometry')
        links_layer=QgsVectorLayer(uri.uri(), 'links_layer', 'spatialite')

        # Import QGIS layer as a panda dataframe and storing features for future copy
        layer = self.parameterAsVectorLayer(parameters, "links", context)
        columns = [parameters['modes'], parameters['link_type']]
        feature_list = []
        row_list = []
        for f in layer.getFeatures():
            geom=f.geometry()
            geom.transform(QgsCoordinateTransform(layer.crs(), aeq_crs, QgsProject.instance()))
            nf=QgsFeature(links_layer.fields())
            nf.setGeometry(geom)
            nf['ogc_fid'] = f[parameters['link_id']]
            nf['link_id'] = f[parameters['link_id']]
            nf['a_node'] = 0
            nf['b_node'] = 0
            nf['source_id'] = f[parameters['link_id']]
            nf['direction'] = f[parameters['direction']]
            nf['link_type'] = f[parameters['link_type']]
            nf['modes'] = f[parameters['modes']]
            feature_list.append(nf)
            row_list.append([f[parameters['modes']], f[parameters['link_type']]])
        df = pd.DataFrame(row_list, columns=columns)
        feedback.pushInfo(" ")
        feedback.setCurrentStep(1)

        feedback.pushInfo(self.tr("Getting parameters from layer"))

        # Updating link types
        link_types = df[parameters["link_type"]].unique()
        lt = project.network.link_types
        lt_dict = lt.all_types()

        existing_types = [ltype.link_type for ltype in lt_dict.values()]
        types_to_add = [ltype for ltype in link_types if ltype not in existing_types]
        for i, ltype in enumerate(types_to_add):
            new_type = lt.new(ascii_lowercase[i])
            new_type.link_type = ltype
            new_type.save()

        # Updating modes
        md = project.network.modes
        md_dict = md.all_modes()
        existing_modes = {k: v.mode_name for k, v in md_dict.items()}

        all_modes = set("".join(df[parameters["modes"]].unique()))
        modes_to_add = [mode for mode in all_modes if mode not in existing_modes]
        for i, mode_id in enumerate(modes_to_add):
            new_mode = md.new(mode_id)
            new_mode.mode_name = f"Mode_from_original_data_{mode_id}"
            project.network.modes.add(new_mode)
            new_mode.save()
        project.close()
        feedback.pushInfo(" ")
        feedback.setCurrentStep(2)

        feedback.pushInfo(self.tr("Adding links"))

        # Adding links all at once
        links_layer.startEditing()
        links_layer.addFeatures(feature_list)        
        links_layer.commitChanges()

        feedback.pushInfo(" ")
        feedback.setCurrentStep(3)

        feedback.pushInfo(self.tr("Closing project"))
        del df, row_list, feature_list

        return {"Output": project_path}

    def name(self):
        return self.tr("Create project from link layer")

    def displayName(self):
        return self.tr("Create project from link layer")

    def group(self):
        return ("01-"+self.tr("Model Building"))

    def groupId(self):
        return ("01-"+self.tr("Model Building"))

    def shortHelpString(self):
        return self.tr("Create an AequilibraE project from a given link layer")

    def createInstance(self):
        return ProjectFromLayer()

    def tr(self, message):
        return trlt("ProjectFromLayer", message)
