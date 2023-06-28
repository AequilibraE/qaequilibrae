"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Auxiliary function with AequilibraE's standard color ramps
 Purpose:    Provide color ramps that make sense for Transportation

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    2016-12-07
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXTtxt_ramp
 -----------------------------------------------------------------------------------------------------------
 """
from qgis.core import QgsVectorGradientColorRampV2

AequilibraERamps = {}

BlueGreenYellowRedBlack = QgsVectorGradientColorRampV2.create(
    {
        "color1": "36,219,255",  # Blue from 0 forward
        "color2": "0,0,0",  # Black at 100%
        "stops": "0.25;0,230,0:" "0.50;255,248,0:" "0.75;252,0,0",  # Green from 25% forward  # Yellow from 50% forward
    }
)  # Red from 75% forward
AequilibraERamps["Blue-Green-Yellow-Red-Black"] = BlueGreenYellowRedBlack


GreenYellowRedBlack = QgsVectorGradientColorRampV2.create(
    {
        "color1": "0,230,0",  # Green from 0% forward
        "color2": "0,0,0",  # Black at 100%
        "stops": "0.25;255,248,0:" "0.50;252,0,0",  # Yellow from 25% forward
    }
)  # Red from 50% forward
AequilibraERamps["Green-Yellow-Red-Black"] = GreenYellowRedBlack
