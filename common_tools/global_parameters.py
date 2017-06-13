from qgis.core import *

# point_types = [QGis.WKBPoint, QGis.WKBMultiPoint, QGis.WKBPoint25D, QGis.WKBMultiPoint25D]
# line_types =  [QGis.WKBLineString, QGis.WKBMultiLineString, QGis.WKBLineString25D, QGis.WKBMultiLineString25D]
# poly_types = [QGis.WKBPolygon, QGis.WKBMultiPolygon, QGis.WKBPolygon25D, QGis.WKBMultiPolygon25D]

point_types = [QGis.WKBPoint, QGis.WKBPoint25D]
line_types =  [QGis.WKBLineString, QGis.WKBLineString25D]
poly_types = [QGis.WKBPolygon, QGis.WKBPolygon25D]

multi_poly = [QGis.WKBMultiPolygon]
multi_line =  [QGis.WKBMultiLineString]
multi_point = [QGis.WKBMultiPoint]

integer_types = [2, 4]
float_types = [6]
string_types = [10]
numeric_types = integer_types + float_types

directions_dictionary = {'AB': 1,
                         'BA': -1,
                         1: 'AB',
                         -1: 'BA'
                        }


reserved_fields = ['A_Node', 'B_node']


