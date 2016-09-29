"""
/***************************************************************************
 AequilibraE - www.aequilibrae.com
 
    Name:        AequilibraE auxiliary Functions
                              -------------------
        begin                : 2014-03-19
        copyright            : AequilibraE developers 2014
        Original Author: Pedro Camargo pedro@xl-optim.com
        Contributors: 
        Licence: See LICENSE.TXT
 ***************************************************************************/
"""

#from qgis.core import *
#import qgis
import math
import os
import yaml

def main():
    pass

#Just a shorthand function to return the current standard path
def standard_path():
    return get_parameter_chain(['system', 'default_directory'])

# Returns the parameter for a given hierarchy of groups in a dictionary of dictionaries (recovered from a Yaml)
def get_parameter_chain(chain):
    head = chain.pop(0)
    g = get_parameters_group(head)
    while len(chain) > 0:
        head = chain.pop(0)
        if head in g:
            g = g[head]
        else:
            chain = []
            g = {}
    return g

# Recovers a group of parameters (or the entire yaml) as a dictionary of dictionaries
def get_parameters_group(group=None):
    path = os.path.dirname(os.path.abspath(__file__)) + "/aequilibrae/"
    with open(path + 'parameters.yml', 'r') as yml:
        path = yaml.safe_load(yml)
    if group is None:
        return path
    if group in path:
        return path[group]
    else:
        return {}


def getVectorLayerByName(layerName):
    layer = QgsMapLayerRegistry.instance().mapLayersByName(layerName)
    if not layer:
        return None
    else:
        return layer[0]


# Haversine formula here:  http://gis.stackexchange.com/questions/44064/how-to-calculate-distances-in-a-point-sequence/56589#56589
def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    meters = 6378137 * c
    return meters

if __name__ == '__main__':
    main()
