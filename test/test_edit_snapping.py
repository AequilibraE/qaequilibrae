import pytest
from qgis.core import Qgis, QgsProject, QgsSnappingConfig, QgsVectorLayer

from qaequilibrae.modules.common_tools import EditSnapping


class FakeMenu:
    """Stands in for AequilibraEMenu, of which EditSnapping only uses the layer pool"""

    def __init__(self):
        self.layers = {}

    def add(self, layer):
        self.layers[layer.name()] = [layer, layer.id()]


def live_settings():
    """Individual layer settings currently on the QGIS project, keyed by layer name"""
    config = QgsProject.instance().snappingConfig()
    return {layer.name(): setting for layer, setting in config.individualLayerSettings().items()}


@pytest.fixture
def layers(qgis_iface):
    links = QgsVectorLayer("LineString?crs=epsg:4326", "links", "memory")
    nodes = QgsVectorLayer("Point?crs=epsg:4326", "nodes", "memory")
    unrelated = QgsVectorLayer("Polygon?crs=epsg:4326", "unrelated", "memory")
    QgsProject.instance().addMapLayers([links, nodes, unrelated])
    yield links, nodes, unrelated
    QgsProject.instance().removeAllMapLayers()


@pytest.fixture
def snapping(layers):
    links, nodes, _ = layers
    menu = FakeMenu()
    menu.add(links)
    menu.add(nodes)

    snap = EditSnapping(menu)
    snap.watch(links)
    snap.watch(nodes)
    return snap


@pytest.fixture
def known_config():
    """Leaves the project on a configuration a restore can be recognized by"""
    config = QgsSnappingConfig(QgsProject.instance().snappingConfig())
    config.setEnabled(False)
    config.setMode(Qgis.SnappingMode.AllLayers)
    config.setTolerance(7.0)
    QgsProject.instance().setSnappingConfig(config)
    return config


def test_editing_turns_snapping_on_for_the_model_layers(snapping, layers):
    links, _, _ = layers
    links.startEditing()

    config = QgsProject.instance().snappingConfig()
    assert config.enabled()
    assert config.mode() == Qgis.SnappingMode.AdvancedConfiguration

    settings = live_settings()
    for name in ["links", "nodes"]:
        assert settings[name].enabled(), f"{name} should be a snapping target"
        assert settings[name].typeFlag() == Qgis.SnappingTypes(Qgis.SnappingType.Vertex)


def test_layers_outside_the_model_are_not_snapped_to(snapping, layers):
    links, _, _ = layers
    links.startEditing()

    assert not live_settings()["unrelated"].enabled()


def test_editing_any_model_layer_snaps_to_all_of_them(snapping, layers):
    _, nodes, _ = layers
    nodes.startEditing()

    settings = live_settings()
    assert settings["links"].enabled()
    assert settings["nodes"].enabled()


def test_configuration_is_restored_when_editing_stops(snapping, layers, known_config):
    links, _, _ = layers

    links.startEditing()
    assert QgsProject.instance().snappingConfig().enabled()

    links.rollBack()

    config = QgsProject.instance().snappingConfig()
    assert not config.enabled()
    assert config.mode() == Qgis.SnappingMode.AllLayers
    assert config.tolerance() == 7.0


def test_configuration_is_restored_only_after_the_last_layer_stops(snapping, layers, known_config):
    links, nodes, _ = layers

    links.startEditing()
    nodes.startEditing()

    links.rollBack()
    assert QgsProject.instance().snappingConfig().enabled(), "nodes is still being edited"

    nodes.rollBack()
    assert not QgsProject.instance().snappingConfig().enabled()


def test_removing_a_layer_while_editing_restores_the_configuration(snapping, layers, known_config):
    links, _, _ = layers
    layer_id = links.id()

    links.startEditing()
    assert QgsProject.instance().snappingConfig().enabled()

    # Removal does not emit editingStopped, so the menu forwards it instead
    QgsProject.instance().removeMapLayer(layer_id)
    snapping.layer_removed(layer_id)

    config = QgsProject.instance().snappingConfig()
    assert not config.enabled()
    assert config.mode() == Qgis.SnappingMode.AllLayers


def test_unloaded_layers_are_not_snapping_targets(snapping, layers):
    links, _, _ = layers

    # The menu keeps layers built but never added to the QGIS project
    loose = QgsVectorLayer("LineString?crs=epsg:4326", "loose", "memory")
    snapping.qgis_project.add(loose)
    snapping.watch(loose)

    links.startEditing()

    assert "loose" not in live_settings()
    assert [layer.name() for layer in snapping.model_layers()] == ["links", "nodes"]
