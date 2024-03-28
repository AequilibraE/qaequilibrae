from qgis.core import QgsProject

from qaequilibrae.modules.gis.least_common_denominator_dialog import LeastCommonDenominatorDialog


def test_least_common_denominator(ae_with_project):
    zones_layer = ae_with_project.layers["zones"][0]
    QgsProject.instance().addMapLayer(zones_layer)

    dialog = LeastCommonDenominatorDialog(ae_with_project)
    dialog._testing = True

    dialog.fromlayer.setCurrentText("zones")
    dialog.tolayer.setCurrentText("zones")
    dialog.tofield.setCurrentIndex(1)
    dialog.fromfield.setCurrentIndex(1)

    dialog.progress_range_from_thread(100)
    dialog.progress_value_from_thread(100)
    dialog.progress_text_from_thread("100")
    dialog.run()
    dialog.worker_thread.doWork()
    dialog.finished_threaded_procedure()

    dialog.close()

    layers_names = [layer.name() for layer in QgsProject.instance().mapLayers().values()]
    assert "output" in layers_names

    layer = QgsProject.instance().mapLayersByName("output")[0]
    assert layer.dataProvider().featureCount() == 3
