import pytest
from os.path import isdir
from pathlib import Path
from shutil import rmtree

from qaequilibrae.modules.project_procedures.create_examples_dialog import CreateExampleDialog


@pytest.mark.parametrize("place_name", ["coquimbo", "nauru", "sioux_falls"])
def test_create_example(ae, place_name):
    dialog = CreateExampleDialog(ae)

    dialog.place = place_name
    dialog.output_path.setText(f"example_{place_name}")

    dialog.run()

    folder = Path(f"example_{place_name}")
    assert isdir(folder)

    rmtree(folder)
