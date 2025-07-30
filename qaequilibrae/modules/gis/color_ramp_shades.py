from qgis.core import QgsStyle


def color_ramp_shades(colormap: str, nclass: int, invert: bool):
    ramp = QgsStyle().defaultStyle().colorRamp(colormap)
    if not invert:
        return [ramp.color(i / nclass) for i in range(nclass + 1)]
    else:
        return [ramp.color(1 - (i / nclass)) for i in range(nclass + 1)]
