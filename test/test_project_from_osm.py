import pytest

from qaequilibrae.modules.project_procedures.project_from_osm_dialog import ProjectFromOSMDialog


@pytest.mark.skip("Not working")
def test_project_from_osm(ae, folder_path):
    dialog = ProjectFromOSMDialog(ae)
    dialog.path = folder_path

    dialog.choose_place.setChecked(True)
    dialog.place.setText("Nauru")

    dialog.output_path.setText("test_from_osm")

    dialog.run()

    print(dialog.__dict__)
    dialog.close()
