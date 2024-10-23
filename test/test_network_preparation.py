import pytest
from os.path import join
from uuid import uuid4
from shutil import copytree

from qgis.core import QgsProject, QgsVectorLayer
from qaequilibrae.modules.network.network_preparation_dialog import NetworkPreparationDialog
from qaequilibrae.modules.network.Network_preparation_procedure import NetworkPreparationProcedure


def load_test_layer(path, file_name):
    csv_path = f"/{path}/{file_name}.csv"

    if file_name == "link":
        uri = "file://{}?delimiter=,&crs=epsg:4326&wktField={}".format(csv_path, "geometry")
    else:
        uri = "file://{}?delimiter=,&crs=epsg:4326&xField={}&yField={}".format(csv_path, "x", "y")

    layer = QgsVectorLayer(uri, file_name, "delimitedtext")

    if not layer.isValid():
        print("Layer failed to load!")
    else:
        QgsProject.instance().addMapLayer(layer)


@pytest.mark.parametrize("is_node", [True, False])
def test_prepare_network(tmp_path, ae, is_node):

    folder = join(tmp_path, uuid4().hex)
    copytree("test/data/NetworkPreparation", folder)

    load_test_layer(folder, "link")
    if is_node:
        load_test_layer(folder, "node")

    dialog = NetworkPreparationDialog(ae)
    dialog.cbb_line_layer.setCurrentText("link")
    dialog.OutLinks.setText("net_links")
    if is_node:
        dialog.cbb_node_layer.setCurrentText("node")
        dialog.cbb_node_fields.setCurrentText("node_id")
        dialog.worker_thread = NetworkPreparationProcedure(
            ae.iface.mainWindow(),
            dialog.cbb_line_layer.currentText(),
            dialog.OutLinks.text(),
            node_layer=dialog.cbb_node_layer.currentText(),
            node_ids=dialog.cbb_node_fields.currentText(),
        )
    else:
        dialog.OutNodes.setText("net_nodes")
        dialog.np_node_start.setText("1001")
        dialog.worker_thread = NetworkPreparationProcedure(
            ae.iface.mainWindow(),
            dialog.cbb_line_layer.currentText(),
            dialog.OutLinks.text(),
            new_node_layer=dialog.OutNodes.text(),
            node_start=int(dialog.np_node_start.text()),
        )

    dialog.worker_thread.signal.connect(dialog.signal_handler)
    dialog.worker_thread.doWork()

    all_layers = [layer.name() for layer in QgsProject.instance().mapLayers().values()]
    assert "net_links" in all_layers

    if not is_node:
        assert "net_nodes" in all_layers

        layer = QgsProject.instance().mapLayersByName("net_nodes")[0]
        for f in layer.getFeatures():
            assert f.attributes()[0] >= 1001

    QgsProject.instance().removeAllMapLayers()
