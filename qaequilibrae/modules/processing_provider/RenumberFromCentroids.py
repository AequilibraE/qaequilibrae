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
from os.path import join
from shapely.wkt import loads as load_wkt
import pandas as pd

class RenumberFromCentroids(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('nodes', 'Nodes', types=[QgsProcessing.TypeVectorPoint], defaultValue='nodes'))
        self.addParameter(QgsProcessingParameterField('node_id', 'Node id', type=QgsProcessingParameterField.Numeric, parentLayerParameterName='nodes', allowMultiple=False, defaultValue='node_id'))
        self.addParameter(QgsProcessingParameterFile('PrjtPath', 'AequilibraE project', behavior=QgsProcessingParameterFile.Folder, fileFilter='Tous les fichiers (*.*)', defaultValue='D:/'))

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(3, model_feedback)
        results = {}
        outputs = {}
        
        output_file='AequilibraE librairy is not available'
        # Checks if aequilibrae is available (not directly available at QGIS startup)
        spec = iutil.find_spec("aequilibrae")
        has_aeq = spec is not None
        if has_aeq:
            from aequilibrae import Project
            feedback.pushInfo('Connecting to aequilibrae project')
            project = Project()
            project.open(parameters['PrjtPath'])
            feedback.pushInfo(' ')
            feedback.setCurrentStep(1)
            
            feedback.pushInfo('Importing node layer from QGIS')
            layer_crs = self.parameterAsVectorLayer(parameters, 'nodes', context).crs()
            aeq_crs = QgsCoordinateReferenceSystem("EPSG:4326")
            
            #Import QGIS layer as a panda dataframe
            layer = self.parameterAsVectorLayer(parameters, 'nodes', context)
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
            
            feedback.pushInfo('Looking for existing nodes from AequilibraE project')
            #Import QGIS layer as a panda dataframe
            all_nodes = project.network.nodes
            nodes_table= all_nodes.data
            
            def format_XY(geometry):
                formated = str(round(float(str(geometry)[7:-1].split(" ")[0]),8))+'_'+str(round(float(str(geometry)[7:-1].split(" ")[1]),8))
                return formated
            
            feedback.pushInfo('Comparing nodes from input centroid layer:')  
            df['XY']=df.apply(lambda row: format_XY(row.geometry), axis=1)
            feedback.pushInfo(str(df.XY.head(5)))
            feedback.pushInfo('With existing nodes in AequilibraE project:')
            nodes_table['XY']=nodes_table.apply(lambda row: format_XY(row.geometry), axis=1)
            feedback.pushInfo(str(nodes_table.XY.head(5)))
            feedback.pushInfo(' ')

            find=0
            create=0
            fail=0
            for idx, zone in df.iterrows():
                matching=nodes_table[(nodes_table.XY == zone.XY)]
                if (len(matching.index) == 1):
                    find += 1
                    if int(zone[parameters['node_id']]) != int(matching['node_id'].iloc[0]):
                        updt=all_nodes.get(matching['node_id'].iloc[0])
                        updt.is_centroid=1
                        updt.renumber(zone[parameters['node_id']])
                        updt.save()
                elif len(matching.index) == 0 :
                    create += 1
                    new=all_nodes.new_centroid(zone[parameters['node_id']])
                    new.geometry = load_wkt(zone['geometry'])
                    new.save()                    
                elif len(matching.index) > 1 :
                    fail += 1
                    feedback.pushInfo(' Multiple nodes found for zone '+ str(zone[parameters['node_id']])+', can\'t decide the node to use')
            feedback.pushInfo(str(len(df))+' zones found in input layer :')
            if find>0:
                feedback.pushInfo(' •'+str(find)+' zones found an existing matching node')
            if create>0:
                feedback.pushInfo(' •'+str(create)+' new nodes added for unmatched zones')
            if fail>0:
                feedback.pushInfo(' •'+str(fail)+' zones could not be processed')
            feedback.pushInfo(' ')
            
            project.close()
            output_file=parameters['PrjtPath']
        return {'Output': output_file}

    def name(self):
        return 'Create/renumber nodes from a centroid layer'

    def displayName(self):
        return 'Create/renumber nodes from a centroid layer'

    def group(self):
        return '1_Network'

    def groupId(self):
        return '1_Network'

    def shortHelpString(self):
        return """
        Import or create nodes to match an AequilibraE project with a GIS layer of centroids
        Warning : you may have to change existing node_id (ex. using field calculator) so that the zone IDs are not already used when runnning this algorithm.
        """

    def createInstance(self):
        return RenumberFromCentroids()