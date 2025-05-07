from os.path import join

import numpy as np

from qaequilibrae.modules.public_transport_procedures.transit_skimming_and_assignment import TransitSkimAssign
from .utilities import create_matrix


def create_dialog_with_matrix(project):
    pth = join(project.project.project_base_path, "matrices/demand.aem")
    create_matrix(np.arange(1, 134), pth)

    matrices = project.project.matrices
    matrices.update_database()
    matrices.reload()

    return TransitSkimAssign(project)


def test_init(qtbot, coquimbo_project):
    dialog = create_dialog_with_matrix(coquimbo_project)

    for i in [0, 1]:
        path = qtbot.screenshot(dialog.tabWidget.widget(i), suffix=f"{i}")
        print(path)
