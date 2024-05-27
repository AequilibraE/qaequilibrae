from os.path import join
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform
from qgis.core import QgsProcessing, QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer, QgsProcessingParameterField, QgsProcessingParameterFile, \
    QgsProcessingParameterString
from qgis.core import QgsProject, QgsFeature, QgsVectorLayer, QgsDataSourceUri

import importlib.util as iutil
import pandas as pd
import sys
from shapely.wkt import loads as load_wkt
from string import ascii_lowercase

from .translatable_algo import TranslatableAlgorithm


class ProjectFromLayer(TranslatableAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('links', self.tr('Links'), types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterField('link_id', self.tr('Link_ID'), type=QgsProcessingParameterField.Numeric, parentLayerParameterName='links', allowMultiple=False, defaultValue='link_id'))
        self.addParameter(QgsProcessingParameterField('link_type', self.tr('Link_type'), type=QgsProcessingParameterField.String, parentLayerParameterName='links', allowMultiple=False, defaultValue='link_type'))
        self.addParameter(QgsProcessingParameterField('direction', self.tr('Direction'), type=QgsProcessingParameterField.Numeric, parentLayerParameterName='links', allowMultiple=False, defaultValue='direction'))
        self.addParameter(QgsProcessingParameterField('modes', self.tr('Modes'), type=QgsProcessingParameterField.String, parentLayerParameterName='links', allowMultiple=False, defaultValue='modes'))
        self.addParameter(QgsProcessingParameterFile('destFolder', self.tr('Folder to create the project in'), behavior=QgsProcessingParameterFile.Folder, defaultValue='D:/'))
        self.addParameter(QgsProcessingParameterString('prject_name', self.tr('Project name'), multiLine=False, defaultValue='New_Project'))

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)
        
        # Checks if we have access to aequilibrae library
        if iutil.find_spec("aequilibrae") is None:
            sys.exit(self.tr('AequilibraE library not found'))

        from aequilibrae import Project
        
        feedback.pushInfo(self.tr('Generating empty aequilibrae project'))
        project = Project()
        PrjtPath= join(parameters['destFolder'],parameters['prject_name'])
        project.new(PrjtPath)
        
        # Adding source_id field early to have all fields available in links table
        links = project.network.links
        link_data = links.fields
        link_data.add("source_id", "link_id from the data source")
        links.refresh_fields()
        uri = QgsDataSourceUri()
        uri.setDatabase(join(PrjtPath,'project_database.sqlite'))
        uri.setDataSource('', 'links', 'geometry')
        links_layer=QgsVectorLayer(uri.uri(), 'links_layer', 'spatialite')
        feedback.pushInfo(' ')
        feedback.setCurrentStep(1)
        
        feedback.pushInfo(self.tr('Importing link layer from QGIS'))
        layer_crs = self.parameterAsVectorLayer(parameters, 'links', context).crs()
        aeq_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        
        #Import QGIS layer as a panda dataframe and storing features for future copy
        layer = self.parameterAsVectorLayer(parameters, 'links', context)
        columns = [parameters['modes'], parameters['link_type']]
        row_list = []
        featureList = []      
        for f in layer.getFeatures():
            geom=f.geometry()
            geom.transform(QgsCoordinateTransform(layer_crs, aeq_crs, QgsProject.instance()))
            nf=QgsFeature(links_layer.fields())
            nf.setGeometry(geom)
            nf['ogc_fid']=f[parameters['link_id']]
            nf['link_id']=f[parameters['link_id']]
            nf['source_id']=f[parameters['link_id']]
            nf['direction']=f[parameters['direction']]
            nf['link_type']=f[parameters['link_type']]
            nf['modes']=f[parameters['modes']]
            featureList.append(nf)
            row_list.append([f[parameters['modes']], f[parameters['link_type']]])
        df = pd.DataFrame(row_list, columns=columns)
        feedback.pushInfo(' ')
        feedback.setCurrentStep(2)
        
        feedback.pushInfo(self.tr('Getting parameters from link layer and setting up the AequilibraE project'))
        
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
        
        feedback.pushInfo(self.tr('Adding links'))
        
        #Adding links all at once
        links_layer.startEditing()
        links_layer.dataProvider().addFeatures(featureList)        
        links_layer.commitChanges()       
        
        feedback.pushInfo(' ')
        feedback.setCurrentStep(4)
                
        feedback.pushInfo(self.tr('Closing aequilibrae project'))
        project.close()
        del row_list, df, featureList, uri, links_layer
        
        output_file=PrjtPath
        return {'Output': output_file}

    def name(self):
        return self.tr('Create project from link layer')

    def displayName(self):
        return self.tr('Create project from link layer')

    def group(self):
        return self.tr('0_Project')

    def groupId(self):
        return self.tr('0_Project')

    def shortHelpString(self):
        return self.tr("""
        Create an AequilibraE project from a given link layer
        """)

    def createInstance(self):
        return ProjectFromLayer(self.tr)