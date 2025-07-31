import pytest
from qgis.core import QgsProject

from qaequilibrae.modules.gis.simple_tag_dialog import SimpleTagDialog
from qaequilibrae.modules.gis.simple_tag_procedure import SimpleTAG
from .utilities import create_links_layer, create_nodes_layer, create_polygons_layer

linestring_assertions = {
    "polygon": {
        "ENCLOSED": ["La Flor del Aire", None, "Pasaje Las Rosas"],
        "TOUCHING": ["Escorial", None, "Lautaro"],
        "CLOSEST": ["Tres Árboles", "centroid connector zone 98", "Circunvalación Monjitas Oriente"],
    },
    "linestring": {
        "TOUCHING": [None, None, None],
        "CLOSEST": ["Óscar Quiroz Morgado", "centroid connector zone 98", "Guatemala"],
    },
    "point": {"CLOSEST": ["centroid connector zone 97", "centroid connector zone 98", "centroid connector zone 99"]},
}

point_assertions = {
    "polygon": {
        "ENCLOSED": ["rs", None, "lr"],
        "CLOSEST": ["r", "uz", "rt"],
    },
    "linestring": {
        "CLOSEST": ["rs", "z", "lr"],
    },
    "point": {"CLOSEST": ["z", "z", "z"]},
}

places = ["Valparaiso", "Santiago", "Antofagasta"]


@pytest.mark.parametrize("ops", ["ENCLOSED", "TOUCHING", "CLOSEST"])
@pytest.mark.parametrize("to_layer", ["polygon", "linestring", "point"])
def test_simple_tag_polygon(coquimbo_project, to_layer, ops):
    if to_layer == "point" and ops == "TOUCHING":
        pytest.skip(f"'{ops}' does not apply to polygon-{to_layer}")

    coquimbo_project.load_layer_by_name("zones")

    zones = [97, 98, 99]

    with coquimbo_project.project.db_connection as conn:
        for i, zone in enumerate(zones):
            conn.execute(f"UPDATE zones SET name='{places[i]}' WHERE zone_id={zone}")
        conn.execute("DELETE FROM zones WHERE name IS NULL;")

    if to_layer == "polygon":
        layer = create_polygons_layer(zones)
    elif to_layer == "linestring":
        layer = create_links_layer(zones)
    else:
        layer = create_nodes_layer(zones)

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert to_layer in prj_layers
    assert "zones" in prj_layers

    dialog = SimpleTagDialog(coquimbo_project)

    dialog.fromlayer.setCurrentText("zones")
    dialog.fromfield.setCurrentIndex(3)
    dialog.tolayer.setCurrentText(to_layer)
    dialog.tofield.setCurrentIndex(2)

    dialog.set_from_fields()
    dialog.set_to_fields()
    dialog.set_available_operations()

    dialog.worker_thread = SimpleTAG(
        parentThread=coquimbo_project.iface.mainWindow(),
        flayer="zones",
        ffield="name",
        tlayer=to_layer,
        tfield="name",
        fmatch=None,
        tmatch=None,
        operation=ops,
        geo_types=dialog.geography_types,
    )
    dialog.worker_thread.doWork()

    feats = [f["name"] for f in layer.getFeatures()]
    assert "Santiago" in feats
    if ops in ["TOUCHING", "CLOSEST"] or to_layer == "point":
        assert "Valparaiso" in feats
    elif ops in ["CLOSEST"] or to_layer == "point":
        assert "Antofagasta" in feats


@pytest.mark.parametrize("ops", ["ENCLOSED", "TOUCHING", "CLOSEST"])
@pytest.mark.parametrize("to_layer", ["polygon", "linestring", "point"])
def test_simple_tag_linestring(coquimbo_project, to_layer, ops):
    if to_layer != "polygon" and ops == "ENCLOSED":
        pytest.skip(f"'{ops}' does not apply to linestring-{to_layer}")
    if to_layer == "point" and ops == "TOUCHING":
        pytest.skip(f"'{ops}' does not apply to linestring-{to_layer}")

    coquimbo_project.load_layer_by_name("links")

    nodes = [21, 121, 1021]

    if to_layer == "polygon":
        layer = create_polygons_layer(nodes)
    elif to_layer == "linestring":
        layer = create_links_layer(nodes)
    else:
        layer = create_nodes_layer(nodes)

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert to_layer in prj_layers
    assert "links" in prj_layers

    dialog = SimpleTagDialog(coquimbo_project)

    dialog.fromlayer.setCurrentText("links")
    dialog.fromfield.setCurrentIndex(3)
    dialog.tolayer.setCurrentText(to_layer)
    dialog.tofield.setCurrentIndex(2)

    dialog.set_from_fields()
    dialog.set_to_fields()
    dialog.set_available_operations()

    dialog.worker_thread = SimpleTAG(
        parentThread=coquimbo_project.iface.mainWindow(),
        flayer="links",
        ffield="name",
        tlayer=to_layer,
        tfield="name",
        fmatch=None,
        tmatch=None,
        operation=ops,
        geo_types=dialog.geography_types,
    )
    dialog.worker_thread.doWork()

    feats = [f["name"] for f in layer.getFeatures()]
    assert len(feats) == len(linestring_assertions[to_layer][ops])


@pytest.mark.parametrize("ops", ["ENCLOSED", "CLOSEST"])
@pytest.mark.parametrize("to_layer", ["polygon", "linestring", "point"])
def test_simple_tag_point(coquimbo_project, to_layer, ops):
    if to_layer != "polygon" and ops == "ENCLOSED":
        pytest.skip(f"'{ops}' does not apply to point-{to_layer}")

    nodes = [21, 121, 12321]

    coquimbo_project.load_layer_by_name("nodes")

    if to_layer == "polygon":
        layer = create_polygons_layer(nodes)
    elif to_layer == "linestring":
        layer = create_links_layer(nodes)
    else:
        layer = create_nodes_layer(nodes)

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert to_layer in prj_layers
    assert "nodes" in prj_layers

    dialog = SimpleTagDialog(coquimbo_project)

    dialog.fromlayer.setCurrentText("nodes")
    dialog.fromfield.setCurrentIndex(4)
    dialog.tolayer.setCurrentText(to_layer)
    dialog.tofield.setCurrentIndex(2)

    dialog.set_from_fields()
    dialog.set_to_fields()
    dialog.set_available_operations()

    dialog.worker_thread = SimpleTAG(
        parentThread=coquimbo_project.iface.mainWindow(),
        flayer="nodes",
        ffield="link_types",
        tlayer=to_layer,
        tfield="name",
        fmatch=None,
        tmatch=None,
        operation=ops,
        geo_types=dialog.geography_types,
    )
    dialog.worker_thread.doWork()

    feats = [f["name"] for f in layer.getFeatures()]
    assert feats == point_assertions[to_layer][ops]
