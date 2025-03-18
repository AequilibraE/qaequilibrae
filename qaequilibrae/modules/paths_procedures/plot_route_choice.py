import numpy as np
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsVectorLayer, QgsProject, QgsField, QgsFeature, QgsSimpleLineSymbolLayer

from qaequilibrae.modules.common_tools.auxiliary_functions import get_vector_layer_by_name


def plot_results(results, from_node, to_node, link_layer):
    links = set_links_width(results)

    exp = '"link_id" IN {}'.format(tuple(links.keys()))
    link_layer.selectByExpression(exp)

    selected_features = [f for f in link_layer.getSelectedFeatures()]

    temp_layer_name = f"route_set-{from_node}-{to_node}"

    # Check if layer exists, and if so, remove it
    lyr = get_vector_layer_by_name(temp_layer_name)
    if lyr is not None:
        QgsProject.instance().removeMapLayers([lyr.id()])

    temp_layer = QgsVectorLayer("LineString?crs={}".format(link_layer.crs().authid()), temp_layer_name, "memory")
    provider = temp_layer.dataProvider()
    provider.addAttributes([QgsField("link_id", QVariant.String), QgsField("probability", QVariant.Double)])
    temp_layer.updateFields()

    features = []
    for feature in selected_features:
        link_id = feature["link_id"]
        feat = QgsFeature()
        feat.setGeometry(feature.geometry())
        feat.setAttributes([link_id, links[link_id]])
        features.append(feat)

    provider.addFeatures(features)

    symbol_layer = create_style()

    temp_layer.renderer().symbol().appendSymbolLayer(symbol_layer)
    temp_layer.renderer().symbol().deleteSymbolLayer(0)
    temp_layer.triggerRepaint()

    QgsProject.instance().addMapLayer(temp_layer)


def set_links_width(results):
    links = {}
    for _, rec in results.iterrows():
        for route in rec["route set"]:
            if route not in links:
                links[route] = 0
            links[route] += rec["probability"]

    return links


def create_style():
    r, g, b = np.random.randint(0, 256, (1, 3)).tolist()[0]

    symbol_layer = QgsSimpleLineSymbolLayer.create({})
    props = symbol_layer.properties()
    props["width_dd_expression"] = 'coalesce(scale_linear("probability", 0, 1, 0, 2), 0)'
    props["color_dd_expression"] = f"color_rgb({r}, {g}, {b})"
    symbol_layer = QgsSimpleLineSymbolLayer.create(props)

    return symbol_layer
