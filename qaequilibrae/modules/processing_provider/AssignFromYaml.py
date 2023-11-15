__author__ = 'Arthur Evrard'

from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterFile

from qaequilibrae.i18n.translator import tr

import importlib.util as iutil
import sys

class TrafficAssignYAML(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFile('confFile', tr('Configuration file (.yaml)'), behavior=QgsProcessingParameterFile.File, fileFilter=tr('Assignment configuration file (*.yaml)'), defaultValue=None))

    def processAlgorithm(self, parameters, context, model_feedback):
        feedback = QgsProcessingMultiStepFeedback(5, model_feedback)
        results = {}
        outputs = {}
        
        # Checks if we have access to aequilibrae library
        has_aeq = iutil.find_spec("aequilibrae") is not None
        
        if not has_aeq:
            sys.exit(tr('AequilibraE library not found'))
        from aequilibrae.paths import TrafficAssignment, TrafficClass
        from aequilibrae.project import Project
        from aequilibrae.matrix import AequilibraeMatrix
        import yaml
        
        feedback.pushInfo(tr('Getting parameters from input yaml file...'))
        pathfile=parameters['confFile']
        with open(pathfile,'r') as f:
            params=yaml.safe_load(f)
        feedback.pushInfo(' ')
        feedback.setCurrentStep(1)
        
        feedback.pushInfo(tr('Opening project and setting up traffic classes...'))
        # Opening project
        project = Project()
        project.open(params["Project"])

        # Creating graph
        project.network.build_graphs()

        # Creating traffic classes
        traffic_classes=[]
        feedback.pushInfo(str(len(params["Traffic_classes"]))+tr(' traffic classes have been find in config file :'))
        for classes in params["Traffic_classes"]:
            for traffic in classes:

                #Getting matrix
                demand = AequilibraeMatrix()
                demand.load(classes[traffic]["matrix_path"])
                demand.computational_view([classes[traffic]["matrix_core"]])

                # Getting graph
                graph = project.network.graphs[classes[traffic]["network_mode"]]
                graph.set_graph("travel_time")
                graph.set_blocked_centroid_flows(False)

                if "skims" in classes[traffic] and classes[traffic]["skims"] is not None:
                    skims=[]
                    for sk in classes[traffic]["skims"].split(","): skims.append(sk.strip())
                    graph.set_skimming(skims)

                # Setting class
                assigclass=TrafficClass(name=traffic, graph=graph, matrix=demand)
                assigclass.set_pce(classes[traffic]["pce"])

                if "fixed_cost" in classes[traffic] and classes[traffic]["fixed_cost"] is not None :
                    if "vot" in classes[traffic] and (type(classes[traffic]["vot"])==int or type(classes[traffic]["vot"])==float):
                        assigclass.set_fixed_cost(classes[traffic]["fixed_cost"])
                        assigclass.set_vot(classes[traffic]["vot"])
                    else:
                        sys.exit("error: fixed_cost must come with a correct value of time")

                # Adding class
                feedback.pushInfo('    - '+traffic+' '+str(classes[traffic]))
                traffic_classes.append(assigclass)
        feedback.pushInfo(' ')
        feedback.setCurrentStep(2)

        # Setting up assignment
        feedback.pushInfo(tr('Setting up assignment...'))
        feedback.pushInfo(str(params["Assignment"]))
        assig = TrafficAssignment()
        assig.set_classes(traffic_classes)
        assig.set_vdf(params["Assignment"]["vdf"])
        assig.set_vdf_parameters({"alpha": params["Assignment"]["alpha"], "beta": params["Assignment"]["beta"]})
        assig.set_capacity_field(params["Assignment"]["capacity_field"])
        assig.set_time_field(params["Assignment"]["time_field"])

        assig.set_algorithm(params["Assignment"]["algorithm"])
        assig.max_iter = params["Assignment"]["max_iter"]
        assig.rgap_target = params["Assignment"]["rgap"]
        
        feedback.pushInfo(' ')
        feedback.setCurrentStep(3)
        
        # Running assignment
        feedback.pushInfo(tr('Running traffic assignment...'))
        assig.execute()
        feedback.pushInfo(' ')
        feedback.setCurrentStep(4)

        # Saving outputs
        feedback.pushInfo(tr('Assignment completed, saving outputs...'))
        feedback.pushInfo(str(assig.report()))
        assig.save_results(params["Run_name"])
        assig.save_skims(params["Run_name"] , which_ones="all", format="omx")
        feedback.pushInfo(' ')
        feedback.setCurrentStep(5)

        project.close()
        
        return {'Output': 'Traffic assignment successfully completed'}

    def name(self):
        return tr('Traffic assignment from a config file')

    def displayName(self):
        return tr('Traffic assignment from a config file')

    def group(self):
        return tr('3_Assignment')

    def groupId(self):
        return tr('3_Assignment')
        
    def shortHelpString(self):
        return tr("""
        Run a traffic assignment using a yaml configuration file. Example of valide configuration file:
        ""
        Project: D:/AequilibraE/Project/

        Run_name: sce_from_yaml

        Traffic_classes:
            - car:
                matrix_path: D:/AequilibraE/Project/matrices/demand.aem
                matrix_core: car
                network_mode: c
                pce: 1
                blocked_centroid_flows: True
                skims: travel_time, distance
            - truck:
                matrix_path: D:/AequilibraE/Project/matrices/demand.aem
                matrix_core: truck
                network_mode: c
                pce: 2
                fixed_cost: toll
                vot: 12
                blocked_centroid_flows: True

        Assignment:
            algorithm: bfw
            vdf: BPR2
            alpha: 0.15
            beta: power
            capacity_field: capacity
            time_field: travel_time
            max_iter: 250
            rgap: 0.00001
        ""
        """)

    def createInstance(self):
        return TrafficAssignYAML()