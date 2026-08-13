from os.path import isdir
from pathlib import Path

import pytest

from qaequilibrae.modules.project_procedures.create_examples_dialog import CreateExampleDialog


@pytest.mark.parametrize("place_name", ["coquimbo", "nauru", "sioux_falls"])
def test_create_example(ae, place_name, folder_path):
    dialog = CreateExampleDialog(ae)

    dialog.place = place_name
    dialog.output_path.setText(f"{folder_path}/example_{place_name}")

    dialog.run()

    folder = Path(f"{folder_path}/example_{place_name}")
    assert isdir(folder)

    ae.run_close_project()


def test_created_example_is_opened_in_the_panel(ae, folder_path):
    """create_example hands back an open project, so the panel shows it instead of the user
    having to go back through Open project for the model they were just given
    """
    dialog = CreateExampleDialog(ae)

    dialog.place = "sioux_falls"
    dialog.output_path.setText(f"{folder_path}/example_sioux_falls")

    dialog.run()

    assert ae.project is not None
    assert ae.available_scenarios == ["root"]
    assert {"links", "nodes"} <= set(ae.layers)
    assert ae.projectManager.count() == 1

    ae.run_close_project()
