from os.path import join
from unittest import mock
import sqlite3

import numpy as np
import pandas as pd
from aequilibrae.parameters import Parameters
from qgis.PyQt.QtCore import Qt

from qaequilibrae.modules.project_procedures.run_module_dialog import RunModuleDialog
from .utilities import create_matrix

functions = {0: "matrix_summary", 1: "graph_summary", 2: "results_summary", 3: "example_function_with_kwargs"}


def create_dialog_with_matrix(project):
    pth = join(project.project.project_base_path, "matrices/demand.aem")
    create_matrix(np.arange(1, 134), pth)

    matrices = project.project.matrices
    matrices.update_database()
    matrices.reload()

    return RunModuleDialog(project)


def test_example_function_with_kwargs(coquimbo_project, qtbot, timeoutDetector):
    # Patch LogDialog to avoid modal exec_ blocking the test
    with mock.patch("qaequilibrae.modules.project_procedures.run_module_dialog.LogDialog") as MockLogDialog:
        # Make exec_ do nothing
        MockLogDialog.return_value.exec_ = lambda *args, **kwargs: None
        MockLogDialog.return_value.show = lambda *args, **kwargs: None

        dialog = RunModuleDialog(coquimbo_project)

        dialog.cob_function.setCurrentIndex(0)
        assert dialog.cob_function.currentText() == functions[3]

        qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

        project_log = dialog.project.log()
        contents = project_log.contents()

        assert "example_function_with_kwargs executed. Check for outputs." in contents[-1]


def test_new_function(coquimbo_project, qtbot, timeoutDetector):
    func_string = """from aequilibrae.context import get_active_project\n
def create_delaunay(source: str, name: str, computational_view: str, result_name: str, overwrite: bool=False):\n
\tfrom aequilibrae.utils.create_delaunay_network import DelaunayAnalysis\n
\tproject = get_active_project()\n
\tmatrix = project.matrices\n
\tmat = matrix.get_matrix(name)\n
\tmat.computational_view(computational_view)\n
\tda = DelaunayAnalysis(project)\n
\tda.create_network(source, overwrite)\n
\tda.assign_matrix(mat, result_name)\n
"""

    folder = coquimbo_project.project.project_base_path

    with open(join(folder, "run", "create_delaunay.py"), "w") as file:
        file.write(func_string)

    with open(join(folder, "run", "__init__.py"), "r") as file:
        lines = file.readlines()

    lines.insert(19, "from .create_delaunay import create_delaunay\n")

    with open(join(folder, "run", "__init__.py"), "w") as file:
        file.writelines(lines)

    p = Parameters(coquimbo_project.project)
    p.parameters["run"]["create_delaunay"] = {}
    p.parameters["run"]["create_delaunay"]["source"] = "zones"
    p.parameters["run"]["create_delaunay"]["name"] = "b''"
    p.parameters["run"]["create_delaunay"]["computational_view"] = "demand"
    p.parameters["run"]["create_delaunay"]["result_name"] = "delaunay_test"
    p.write_back()

    with mock.patch("qaequilibrae.modules.project_procedures.run_module_dialog.LogDialog") as MockLogDialog:
        # Make exec_ do nothing
        MockLogDialog.return_value.exec_ = lambda *args, **kwargs: None
        MockLogDialog.return_value.show = lambda *args, **kwargs: None

        dialog = create_dialog_with_matrix(coquimbo_project)

        assert len(dialog.items) > 1

        dialog.cob_function.setCurrentIndex(0)
        assert dialog.cob_function.currentText() == "create_delaunay"

        qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    res_path = join(coquimbo_project.project.project_base_path, "results_database.sqlite")
    conn = sqlite3.connect(res_path)

    results = pd.read_sql("SELECT * FROM delaunay_test", conn).set_index("link_id")

    assert results.shape != (0, 0)
