from qgis.core import QgsStyle


def color_ramp_shades(colormap: str, nclass: int):
    ramp = QgsStyle().defaultStyle().colorRamp(colormap)
    return [ramp.color(i / nclass) for i in range(nclass + 1)]
