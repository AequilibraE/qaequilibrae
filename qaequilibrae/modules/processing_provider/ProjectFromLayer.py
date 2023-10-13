from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsProject
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterField
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterString
import processing

import importlib.util as iutil
from string import ascii_lowercase
from os.path import join
from shapely.wkt import loads as load_wkt
import pandas as pd

class ProjectFromLayer(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('links', 'Links', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterField('link_id', 'Link_ID', type=QgsProcessingParameterField.Numeric, parentLayerParameterName='links', allowMultiple=False, defaultValue='link_id'))
        self.addParameter(QgsProcessingParameterField('link_type', 'Link_type', type=QgsProcessingParameterField.String, parentLayerParameterName='links', allowMultiple=False, defaultValue='link_type'))
        self.addParameter(QgsProcessingParameterField('direction', 'Direction', type=QgsProcessingParameterField.Numeric, parentLayerParameterName='links', allowMultiple=False, defaultValue='direction'))
        self.addParameter(QgsProcessingParameterField('modes', 'Modes', type=QgsProcessingParameterField.String, parentLayerParameterName='links', allowMultiple=False, defaultValue='modes'))
        self.addParameter(QgsProcessingParameterFile('destFolder', 'Folder to create the project in', behavior=QgsProcessingParameterFile.Folder, fileFilter='Tous les fichiers (*.*)', defaultValue='D:/'))
        self.addParameter(QgsProcessingParameterString('prject_name', 'Project name', multiLine=False, defaultValue='New_Project'))

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)
        results = {}
        outputs = {}
        
        output_file='AequilibraE librairy is not available'
         # Checks if aequilibrae is available (not directly available at QGIS startup)
        spec = iutil.find_spec("aequilibrae")
        has_aeq = spec is not None
        if has_aeq:
            from aequilibrae import Project
            feedback.pushInfo('Generating empty aequilibrae project')
            project = Project()
            PrjtPath= join(parameters['destFolder'],parameters['prject_name'])
            project.new(PrjtPath)
            feedback.setCurrentStep(1)
            
            feedback.pushInfo('Importing link layer from QGIS')
            layer_crs = self.parameterAsVectorLayer(parameters, 'links', context).crs()
            aeq_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            
            ##Import QGIS layer as a panda dataframe
            layer = self.parameterAsVectorLayer(parameters, 'links', context)
            columns = [f.name() for f in layer.fields()] + ['geometry']
            columns_types = [f.typeName() for f in layer.fields()] #
            row_list = []
            for f in layer.getFeatures():
                geom=f.geometry()
                geom.transform(QgsCoordinateTransform(layer_crs, aeq_crs, QgsProject.instance()))
                row_list.append(dict(zip(columns, f.attributes() + [geom.asWkt()])))
            df = pd.DataFrame(row_list, columns=columns)
            feedback.pushInfo(' ')
            feedback.setCurrentStep(2)
            
            feedback.pushInfo('Getting parameters from link layer and setting up the AequilibraE project')
            #Updating link types
            link_types = df[parameters['link_type']].unique()
            lt = project.network.link_types
            lt_dict = lt.all_types()
            existing_types = [ltype.link_type for ltype in lt_dict.values()]
            types_to_add = [ltype for ltype in link_types if ltype not in existing_types]
            for i, ltype in enumerate(types_to_add):
                new_type = lt.new(ascii_lowercase[i])
                new_type.link_type = ltype
                new_type.save()
            #Updating modes
            md = project.network.modes
            md_dict = md.all_modes()
            existing_modes = {k: v.mode_name for k, v in md_dict.items()}
            all_modes = set("".join(df[parameters['modes']].unique()))
            modes_to_add = [mode for mode in all_modes if mode not in existing_modes]
            for i, mode_id in enumerate(modes_to_add):
                new_mode = md.new(mode_id)
                new_mode.mode_name = f"Mode_from_original_data_{mode_id}"
                project.network.modes.add(new_mode)
                new_mode.save()
            feedback.pushInfo(' ')
            feedback.setCurrentStep(3)
            
            feedback.pushInfo('Adding links')
            #adding links
            links = project.network.links
            link_data = links.fields
            link_data.add("source_id", "link_id from the data source")
            links.refresh_fields()
            for idx, record in df.iterrows():
                new_link = links.new()
                new_link.source_id = record[parameters['link_id']]
                new_link.direction = record[parameters['direction']]
                new_link.modes = record[parameters['modes']]
                new_link.link_type = record[parameters['link_type']]
                new_link.geometry = load_wkt(record['geometry'])
                new_link.save()
            feedback.pushInfo(' ')
            feedback.setCurrentStep(4)
            
            #df.to_csv(join(PrjtPath,'links.csv'))
            
            feedback.pushInfo('Closing aequilibrae project')
            project.close()
            
            output_file=PrjtPath
        return {'Output': output_file}

    def name(self):
        return 'Create project from link layer'

    def displayName(self):
        return 'Create project from link layer'

    def group(self):
        return '0_Project'

    def groupId(self):
        return '0_Project'

    def shortHelpString(self):
        return """
        Create an AequilibraE project from a given link layer
        """

    def createInstance(self):
        return ProjectFromLayer()