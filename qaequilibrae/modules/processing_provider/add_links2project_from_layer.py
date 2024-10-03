import importlib.util as iutil
import pandas as pd
import sys
from os.path import join
from string import ascii_lowercase

from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProcessingAlgorithm
from qgis.core import QgsProcessing, QgsProcessingMultiStepFeedback, QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterField, QgsProcessingParameterFile, QgsProcessingParameterString
from qgis.core import QgsProject, QgsFeature, QgsVectorLayer, QgsDataSourceUri

from qaequilibrae.modules.common_tools import standard_path
from qaequilibrae.i18n.translate import trlt


class AddLinksFromLayer(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "links",
                self.tr("Links"),
                types=[QgsProcessing.TypeVectorLine],
                defaultValue=None
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
                "project_path",
                self.tr("Project path"),
                behavior=QgsProcessingParameterFile.Folder,
                defaultValue=standard_path(),
            )
        )

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)

        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr("AequilibraE module not found"))

        from aequilibrae import Project

        aeq_crs = QgsCoordinateReferenceSystem("EPSG:4326")

        feedback.pushInfo(self.tr("Opening project"))
        project_path=parameters["project_path"]
        
        # Import links layer
        uri = QgsDataSourceUri()
        uri.setDatabase(join(project_path,'project_database.sqlite'))
        uri.setDataSource('', 'links', 'geometry')
        links_layer=QgsVectorLayer(uri.uri(), 'links_layer', 'spatialite')
        
        # Get current max link_id
        cols = ["link_id", "ogc_fid"]
        datagen = ([f[col] for col in cols] for f in links_layer.getFeatures())
        links_ids = pd.DataFrame.from_records(data=datagen, columns=cols)
        ogc_id = links_ids['ogc_fid'].max() + 1
        link_id = links_ids['link_id'].max() + 1

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
            nf['ogc_fid'] = int(ogc_id)
            nf['link_id'] = int(link_id)
            nf['a_node'] = 0
            nf['b_node'] = 0
            nf['direction'] = f[parameters['direction']]
            nf['link_type'] = f[parameters['link_type']]
            nf['modes'] = f[parameters['modes']]
            ogc_id = ogc_id + 1
            link_id = link_id + 1
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
        return self.tr("Add links from layer to project")

    def displayName(self):
        return self.tr("Add links from layer to project")

    def group(self):
        return ("01-"+self.tr("Model Building"))

    def groupId(self):
        return ("01-"+self.tr("Model Building"))

    def shortHelpString(self):
        return self.tr("Take links from a layer and add them to an existing AequilibraE project")

    def createInstance(self):
        return AddLinksFromLayer()

    def tr(self, message):
        return trlt("AddLinksFromLayer", message)
