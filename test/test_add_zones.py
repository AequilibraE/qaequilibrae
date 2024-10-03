import pytest
from time import sleep
from aequilibrae.utils.db_utils import commit_and_close
from aequilibrae.project.database_connection import database_connection
from qgis.core import QgsProject

from qaequilibrae.modules.project_procedures.adds_zones_dialog import AddZonesDialog


@pytest.mark.parametrize("create_polygons_layer", [[97, 98, 99]], indirect=True)
def test_add_zones(pt_project, create_polygons_layer):

    dialog = AddZonesDialog(pt_project)
    dialog.chb_add_centroids.setChecked(True)

    dialog.changed_layer()
    dialog.run()

    sleep(2)

    with commit_and_close(database_connection("network")) as conn:
        num_zones = conn.execute("select count(zone_id) from zones").fetchone()[0]

    assert num_zones == 3

    QgsProject.instance().clear()
