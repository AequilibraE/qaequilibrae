from qgis.core import QgsWkbTypes

point_types = [QgsWkbTypes.Type.Point, QgsWkbTypes.Type.Point25D]
line_types = [QgsWkbTypes.Type.LineString, QgsWkbTypes.Type.LineString25D]
poly_types = [QgsWkbTypes.Type.Polygon, QgsWkbTypes.Type.Polygon25D]

multi_poly = [QgsWkbTypes.Type.MultiPolygon]
multi_line = [QgsWkbTypes.Type.MultiLineString]
multi_point = [QgsWkbTypes.Type.MultiPoint]

integer_types = [2, 4]
float_types = [6]
string_types = [10]
numeric_types = integer_types + float_types

directions_dictionary = {"AB": 1, "BA": -1, 1: "AB", -1: "BA"}


reserved_fields = ["A_Node", "B_node"]
