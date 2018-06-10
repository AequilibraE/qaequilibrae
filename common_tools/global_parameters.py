from qgis.core import *

# point_types = [QGis.WKBPoint, QGis.WKBMultiPoint, QGis.WKBPoint25D, QGis.WKBMultiPoint25D]
# line_types =  [QGis.WKBLineString, QGis.WKBMultiLineString, QGis.WKBLineString25D, QGis.WKBMultiLineString25D]
# poly_types = [QGis.WKBPolygon, QGis.WKBMultiPolygon, QGis.WKBPolygon25D, QGis.WKBMultiPolygon25D]

point_types = [QgsWkbTypes.Point, QgsWkbTypes.Point25D]
line_types =  [QgsWkbTypes.LineString, QgsWkbTypes.LineString25D]
poly_types = [QgsWkbTypes.Polygon, QgsWkbTypes.Polygon25D]

multi_poly = [QgsWkbTypes.MultiPolygon]
multi_line =  [QgsWkbTypes.MultiLineString]
multi_point = [QgsWkbTypes.MultiPoint]

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


