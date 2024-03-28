import pytest
import numpy as np
from os.path import join

from qaequilibrae.modules.matrix_procedures.display_aequilibrae_formats_dialog import DisplayAequilibraEFormatsDialog


# TODO: missing AED
@pytest.mark.parametrize("file_name", ["matrices/demand.aem", "matrices/SiouxFalls.omx"])
def test_display_formats_without_project(ae, file_name):
    print("\n", file_name)
    dialog = DisplayAequilibraEFormatsDialog(ae, file_path=f"test/data/SiouxFalls_project/{file_name}")

    dialog.exit_procedure()

    assert dialog.list_cores == ["matrix"]
    assert dialog.list_indices == ["taz"]
    assert dialog.data_to_show.matrix["matrix"].shape == (24, 24)
    assert np.sum(np.nan_to_num(dialog.data_to_show.matrix["matrix"])[:, :]) == 360600


@pytest.mark.parametrize("file_name", ["demand.aem", "SiouxFalls.omx"])
def test_display_formats_with_project(ae_with_project, file_name):
    dialog = DisplayAequilibraEFormatsDialog(
        ae_with_project, join(ae_with_project.project.matrices.fldr, file_name), proj=True
    )

    dialog.exit_procedure()

    assert dialog.list_cores == ["matrix"]
    assert dialog.list_indices == ["taz"]
    assert dialog.data_to_show.matrix["matrix"].shape == (24, 24)
    assert np.sum(np.nan_to_num(dialog.data_to_show.matrix["matrix"])[:, :]) == 360600
