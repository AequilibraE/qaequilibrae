from time import sleep

import qgis

from qaequilibrae.modules.project_procedures.add_zones_procedure import AddZonesProcedure
from qaequilibrae.modules.project_procedures.adds_zones_dialog import AddZonesDialog
from .utilities import create_polygons_layer


def test_add_zones_dialog(pt_project):
    _ = create_polygons_layer([97, 98, 99])

    dialog = AddZonesDialog(pt_project)
    dialog.chb_add_centroids.setChecked(True)

    dialog.changed_layer()
    dialog.run()

    sleep(2)

    assert len(pt_project.project.zoning.all_zones()) == 3


def test_add_zones_procedure(pt_project):
    layer = create_polygons_layer([97, 98, 99])

    corresp = {"zone_id": 0, "area": 0, "name": 0, "population": 0, "employment": 0}

    action = AddZonesProcedure(qgis.utils.iface.mainWindow(), pt_project.project, layer, False, False, corresp)
    action.doWork()

    sleep(2)

    assert len(pt_project.project.zoning.all_zones()) == 3
