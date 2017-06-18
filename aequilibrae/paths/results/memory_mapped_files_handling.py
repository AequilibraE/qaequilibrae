"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Routines for handling data files dictionaries
 Purpose:    Having all this handling in a single place

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-12-09
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """
import yaml

def saveDataFileDictionary(uuid, data_type, dimensions, target_file):
    dictio = {'uuid': uuid,
              'Data Type': data_type,
              'Dimensions': dimensions}

    stream = open(target_file, 'w')
    yaml.dump(dictio, stream, default_flow_style=False)
    stream.close()
