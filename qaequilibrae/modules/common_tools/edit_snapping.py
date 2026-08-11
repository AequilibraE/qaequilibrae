from functools import partial

from qgis.PyQt.QtXml import QDomDocument
from qgis.core import Qgis, QgsProject, QgsSnappingConfig, QgsVectorLayer

# QGIS' own default, used only when the project has no usable tolerance of its own
DEFAULT_TOLERANCE = 12.0


class EditSnapping:
    """Turns vertex snapping on across the AequilibraE layers while any of them is toggled for edit."""

    def __init__(self, qgis_project):
        self.qgis_project = qgis_project
        self.editing = set()
        self.saved_config = None  # type: QDomDocument

    def watch(self, layer: QgsVectorLayer):
        """Makes an AequilibraE layer configure snapping whenever it is toggled for edit"""
        layer.editingStarted.connect(partial(self.edit_started, layer.id()))
        layer.editingStopped.connect(partial(self.edit_stopped, layer.id()))

    def edit_started(self, layer_id: str):
        if not self.editing:
            self.saved_config = QDomDocument("qaequilibrae-snapping")
            self.saved_config.appendChild(self.saved_config.createElement("qgis"))
            QgsProject.instance().snappingConfig().writeProject(self.saved_config)

        self.editing.add(layer_id)
        self.enable_snapping()

    def edit_stopped(self, layer_id: str):
        self.editing.discard(layer_id)
        if self.editing or self.saved_config is None:
            return

        config = QgsSnappingConfig(QgsProject.instance())
        config.readProject(self.saved_config)
        QgsProject.instance().setSnappingConfig(config)
        self.saved_config = None

    def layer_removed(self, layer_id: str):
        """Layers removed from the QGIS project while being edited never emit editingStopped"""
        if layer_id in self.editing:
            self.edit_stopped(layer_id)

    def enable_snapping(self):
        project = QgsProject.instance()
        config = QgsSnappingConfig(project.snappingConfig())
        config.setEnabled(True)
        config.setMode(Qgis.SnappingMode.AdvancedConfiguration)

        tolerance, units = config.tolerance(), config.units()
        if tolerance <= 0:
            tolerance, units = DEFAULT_TOLERANCE, Qgis.MapToolUnit.Pixels

        targets = self.model_layers()
        target_ids = {layer.id() for layer in targets}

        # The advanced configuration inherits QGIS' digitizing defaults, which enable every layer in
        # the project, so the ones that do not belong to the model are explicitly turned off
        for layer in config.individualLayerSettings():
            if layer.id() not in target_ids:
                config.setIndividualLayerSettings(layer, self.layer_settings(False, tolerance, units))

        for layer in targets:
            config.setIndividualLayerSettings(layer, self.layer_settings(True, tolerance, units))

        project.setSnappingConfig(config)

    def model_layers(self):
        """AequilibraE layers currently loaded in the QGIS project."""
        project = QgsProject.instance()
        layers = [project.mapLayer(layer_id) for _, layer_id in self.qgis_project.layers.values()]
        return [layer for layer in layers if isinstance(layer, QgsVectorLayer) and layer.isSpatial()]

    @staticmethod
    def layer_settings(enabled: bool, tolerance: float, units) -> QgsSnappingConfig.IndividualLayerSettings:
        vertex = Qgis.SnappingTypes(Qgis.SnappingType.Vertex)
        return QgsSnappingConfig.IndividualLayerSettings(enabled, vertex, tolerance, units)
