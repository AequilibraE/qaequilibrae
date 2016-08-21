import os
import sys
import yaml
import aequilibrae as ae

class Parameters:
    def __init__(self):
        self.path = os.path.dirname(ae.__file__)

        #We load the parameters from our parameter file
        self.path = os.path.dirname(ae.distribution.__file__)

        with open(self.path + '/parameters.yaml', 'r') as yml:
            self.parameters = yaml.load(yml)

    def write_back(self):
        stream = open(self.path + '/parameters.yaml', 'w')
        yaml.dump(self.parameters, stream, default_flow_style=False)
        stream.close()