from qgis.core import QgsProject, QgsLayerTreeLayer


def all_layers_from_toc():
    toc = QgsProject.instance().layerTreeRoot()
    return [child.layer() for child in toc.children() if isinstance(child, QgsLayerTreeLayer)]
