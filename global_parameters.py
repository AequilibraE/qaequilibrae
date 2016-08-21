from qgis.core import *

# point_types = [QGis.WKBPoint, QGis.WKBMultiPoint, QGis.WKBPoint25D, QGis.WKBMultiPoint25D]
# line_types =  [QGis.WKBLineString, QGis.WKBMultiLineString, QGis.WKBLineString25D, QGis.WKBMultiLineString25D]
# poly_types = [QGis.WKBPolygon, QGis.WKBMultiPolygon, QGis.WKBPolygon25D, QGis.WKBMultiPolygon25D]

point_types = [QGis.WKBPoint, QGis.WKBPoint25D]
line_types =  [QGis.WKBLineString, QGis.WKBLineString25D]
poly_types = [QGis.WKBPolygon, QGis.WKBPolygon25D]


integer_types = [2, 4]
float_types = [6]
string_types = [10]
numeric_types = integer_types + float_types